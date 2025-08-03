package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/go-redis/redis/v8"
	"github.com/google/uuid"
	"github.com/streadway/amqp"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

// Configuration
type Config struct {
	DatabaseURL    string
	RabbitMQURL    string
	RedisURL       string
	IoTGatewayURL  string
}

// Device event from RabbitMQ
type DeviceEvent struct {
	DeviceID   string    `json:"device_id"`
	EventType  string    `json:"event_type"`
	Timestamp  time.Time `json:"timestamp"`
	DeviceData Device    `json:"device_data"`
}

// Telemetry event from RabbitMQ (from IoT Gateway)
type TelemetryMessage struct {
	MessageType string        `json:"messageType"`
	Payload     TelemetryData `json:"payload"`
}

type TelemetryData struct {
	TelemetryID string                 `json:"telemetry_id"`
	DeviceID    string                 `json:"device_id"`
	Timestamp   string                 `json:"timestamp"`
	Type        string                 `json:"type"`
	Value       map[string]interface{} `json:"value"`
}

// Batch telemetry event
type TelemetryBatchMessage struct {
	MessageType string             `json:"messageType"`
	Payload     TelemetryBatchData `json:"payload"`
}

type TelemetryBatchData struct {
	BatchID       string                   `json:"batch_id"`
	DeviceID      string                   `json:"device_id"`
	Timestamp     string                   `json:"timestamp"`
	Count         int                      `json:"count"`
	TelemetryData []TelemetryDataPoint     `json:"telemetry_data"`
}

type TelemetryDataPoint struct {
	TelemetryID string                 `json:"telemetry_id"`
	Type        string                 `json:"type"`
	Timestamp   string                 `json:"timestamp"`
	Value       map[string]interface{} `json:"value"`
}

// Device model (matches API)
type Device struct {
	DeviceID   string    `json:"device_id" gorm:"primaryKey;type:uuid"`
	SerialID   string    `json:"serial_id"`
	Name       string    `json:"name"`
	Type       string    `json:"type"`
	Status     string    `json:"status"`
	CreatedAt  time.Time `json:"created_at"`
	UpdatedAt  time.Time `json:"updated_at"`
}

// Telemetry model
type Telemetry struct {
	TelemetryID string                 `json:"telemetry_id" gorm:"primaryKey;type:uuid"`
	DeviceID    string                 `json:"device_id" gorm:"type:uuid"`
	Value       map[string]interface{} `json:"value" gorm:"type:jsonb"`
	Type        string                 `json:"type"`
	CreatedAt   time.Time              `json:"created_at"`
}

// Worker manages device events
type Worker struct {
	config   Config
	db       *gorm.DB
	redis    *redis.Client
	rabbitmq *amqp.Connection
	channel  *amqp.Channel
	ctx      context.Context
}

func main() {
	log.Println("🚀 Starting Device Management Worker")

	config := Config{
		DatabaseURL:   getEnv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/management_db"),
		RabbitMQURL:   getEnv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/"),
		RedisURL:      getEnv("REDIS_URL", "redis://redis:6379"),
		IoTGatewayURL: getEnv("IOT_GATEWAY_URL", "http://iot-gateway:8080"),
	}

	worker, err := NewWorker(config)
	if err != nil {
		log.Fatalf("❌ Failed to create worker: %v", err)
	}
	defer worker.Close()


	go worker.ConsumeDeviceEvents()
	go worker.ConsumeTelemetryEvents()


	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)
	<-c

	log.Println("👋 Shutting down Device Management Worker")
}

func NewWorker(config Config) (*Worker, error) {
	ctx := context.Background()


	db, err := gorm.Open(postgres.Open(config.DatabaseURL), &gorm.Config{})
	if err != nil {
		return nil, fmt.Errorf("failed to connect to database: %w", err)
	}


	err = db.AutoMigrate(&Device{}, &Telemetry{})
	if err != nil {
		return nil, fmt.Errorf("failed to migrate database: %w", err)
	}


	opt, err := redis.ParseURL(config.RedisURL)
	if err != nil {
		return nil, fmt.Errorf("failed to parse Redis URL: %w", err)
	}
	rdb := redis.NewClient(opt)


	_, err = rdb.Ping(ctx).Result()
	if err != nil {
		return nil, fmt.Errorf("failed to connect to Redis: %w", err)
	}


	conn, err := amqp.Dial(config.RabbitMQURL)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to RabbitMQ: %w", err)
	}

	ch, err := conn.Channel()
	if err != nil {
		return nil, fmt.Errorf("failed to open channel: %w", err)
	}


	_, err = ch.QueueDeclare(
		"devices",
		true,
		false,
		false,
		false,
		nil,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to declare queue: %w", err)
	}


	err = ch.ExchangeDeclare(
		"telemetry",
		"topic",
		true,
		false,
		false,
		false,
		nil,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to declare telemetry exchange: %w", err)
	}


	telemetryQueue, err := ch.QueueDeclare(
		"telemetry.management",
		true,
		false,
		false,
		false,
		nil,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to declare telemetry queue: %w", err)
	}


	err = ch.QueueBind(
		telemetryQueue.Name,
		"telemetry.*",
		"telemetry",
		false,
		nil,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to bind telemetry queue: %w", err)
	}

	log.Println("✅ Worker initialized successfully")

	return &Worker{
		config:   config,
		db:       db,
		redis:    rdb,
		rabbitmq: conn,
		channel:  ch,
		ctx:      ctx,
	}, nil
}

func (w *Worker) ConsumeDeviceEvents() {
	msgs, err := w.channel.Consume(
		"devices",
		"",
		true,
		false,
		false,
		false,
		nil,
	)
	if err != nil {
		log.Fatalf("❌ Failed to register consumer: %v", err)
	}

	log.Println("📡 Started consuming device events from RabbitMQ")

	for msg := range msgs {
		w.processDeviceEvent(msg.Body)
	}
}

func (w *Worker) ConsumeTelemetryEvents() {
	msgs, err := w.channel.Consume(
		"telemetry.management",
		"",
		true,
		false,
		false,
		false,
		nil,
	)
	if err != nil {
		log.Fatalf("❌ Failed to register telemetry consumer: %v", err)
	}

	log.Println("📊 Started consuming telemetry events from RabbitMQ")

	for msg := range msgs {
		w.processTelemetryEvent(msg.Body)
	}
}

func (w *Worker) processDeviceEvent(body []byte) {
	var event DeviceEvent
	if err := json.Unmarshal(body, &event); err != nil {
		log.Printf("❌ Failed to parse device event: %v", err)
		return
	}

	log.Printf("📨 Processing device event: %s for device %s", event.EventType, event.DeviceID)

	switch event.EventType {
	case "registered":
		w.handleDeviceRegistered(event)
	case "updated":
		w.handleDeviceUpdated(event)
	default:
		log.Printf("⚠️ Unknown event type: %s", event.EventType)
	}
}

func (w *Worker) handleDeviceRegistered(event DeviceEvent) {

	device := Device{
		DeviceID:  event.DeviceData.DeviceID,
		SerialID:  event.DeviceData.SerialID,
		Name:      event.DeviceData.Name,
		Type:      event.DeviceData.Type,
		Status:    event.DeviceData.Status,
		CreatedAt: event.DeviceData.CreatedAt,
		UpdatedAt: event.DeviceData.UpdatedAt,
	}

	result := w.db.Create(&device)
	if result.Error != nil {
		log.Printf("❌ Failed to create device in management DB: %v", result.Error)
		return
	}


	go w.updateDeviceStatusCache(event.DeviceID)

	log.Printf("✅ Device registered in management system: %s", event.DeviceID)
}

func (w *Worker) handleDeviceUpdated(event DeviceEvent) {

	device := Device{
		DeviceID:  event.DeviceData.DeviceID,
		SerialID:  event.DeviceData.SerialID,
		Name:      event.DeviceData.Name,
		Type:      event.DeviceData.Type,
		Status:    event.DeviceData.Status,
		UpdatedAt: event.DeviceData.UpdatedAt,
	}

	result := w.db.Model(&Device{}).Where("device_id = ?", event.DeviceID).Updates(device)
	if result.Error != nil {
		log.Printf("❌ Failed to update device in management DB: %v", result.Error)
		return
	}


	go w.updateDeviceStatusCache(event.DeviceID)

	log.Printf("✅ Device updated in management system: %s", event.DeviceID)
}

func (w *Worker) updateDeviceStatusCache(deviceID string) {

	url := fmt.Sprintf("%s/devices/%s/status", w.config.IoTGatewayURL, deviceID)
	resp, err := http.Get(url)
	if err != nil {
		log.Printf("⚠️ Failed to get device status from IoT Gateway: %v", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		log.Printf("⚠️ IoT Gateway returned status %d for device %s", resp.StatusCode, deviceID)
		return
	}

	var statusData map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&statusData); err != nil {
		log.Printf("❌ Failed to decode status response: %v", err)
		return
	}


	statusJSON, _ := json.Marshal(statusData)
	cacheKey := fmt.Sprintf("device:status:%s", deviceID)
	err = w.redis.Set(w.ctx, cacheKey, statusJSON, 5*time.Minute).Err()
	if err != nil {
		log.Printf("❌ Failed to cache device status: %v", err)
		return
	}


	if telemetryData, ok := statusData["telemetry"]; ok {
		w.storeTelemetry(deviceID, telemetryData)
	}

	log.Printf("📦 Cached status for device %s", deviceID)
}

func (w *Worker) processTelemetryEvent(body []byte) {

	var telemetryMsg TelemetryMessage
	if err := json.Unmarshal(body, &telemetryMsg); err == nil {
		if telemetryMsg.MessageType == "telemetryReceived" {
			w.storeTelemetryFromEvent(telemetryMsg.Payload)
			return
		}
	}


	var batchMsg TelemetryBatchMessage
	if err := json.Unmarshal(body, &batchMsg); err == nil {
		if batchMsg.MessageType == "telemetryBatch" {
			w.storeTelemetryBatch(batchMsg.Payload)
			return
		}
	}

	log.Printf("⚠️ Unknown telemetry message format: %s", string(body))
}

func (w *Worker) storeTelemetryFromEvent(data TelemetryData) {

	timestamp, err := time.Parse(time.RFC3339, data.Timestamp)
	if err != nil {
		log.Printf("⚠️ Failed to parse timestamp: %v, using current time", err)
		timestamp = time.Now()
	}

	telemetry := Telemetry{
		TelemetryID: data.TelemetryID,
		DeviceID:    data.DeviceID,
		Value:       data.Value,
		Type:        data.Type,
		CreatedAt:   timestamp,
	}

	result := w.db.Create(&telemetry)
	if result.Error != nil {
		log.Printf("❌ Failed to store telemetry for device %s: %v", data.DeviceID, result.Error)
		return
	}


	w.cacheTelemetry(telemetry)

	log.Printf("📊 Stored telemetry %s for device %s (type: %s)", data.TelemetryID, data.DeviceID, data.Type)
}

func (w *Worker) storeTelemetryBatch(batch TelemetryBatchData) {
	log.Printf("📦 Processing telemetry batch %s with %d entries for device %s", batch.BatchID, batch.Count, batch.DeviceID)

	for _, dataPoint := range batch.TelemetryData {

		timestamp, err := time.Parse(time.RFC3339, dataPoint.Timestamp)
		if err != nil {
			log.Printf("⚠️ Failed to parse timestamp: %v, using current time", err)
			timestamp = time.Now()
		}

		telemetry := Telemetry{
			TelemetryID: dataPoint.TelemetryID,
			DeviceID:    batch.DeviceID,
			Value:       dataPoint.Value,
			Type:        dataPoint.Type,
			CreatedAt:   timestamp,
		}

		result := w.db.Create(&telemetry)
		if result.Error != nil {
			log.Printf("❌ Failed to store batch telemetry %s: %v", dataPoint.TelemetryID, result.Error)
			continue
		}


		w.cacheTelemetry(telemetry)
	}

	log.Printf("✅ Processed telemetry batch %s (%d entries)", batch.BatchID, len(batch.TelemetryData))
}

func (w *Worker) cacheTelemetry(telemetry Telemetry) {
	telemetryJSON, _ := json.Marshal(telemetry)
	cacheKey := fmt.Sprintf("device:telemetry:latest:%s", telemetry.DeviceID)
	err := w.redis.Set(w.ctx, cacheKey, telemetryJSON, 1*time.Hour).Err()
	if err != nil {
		log.Printf("⚠️ Failed to cache telemetry for device %s: %v", telemetry.DeviceID, err)
	}
}

func (w *Worker) storeTelemetry(deviceID string, telemetryData interface{}) {
	telemetry := Telemetry{
		TelemetryID: generateUUID(),
		DeviceID:    deviceID,
		Value:       telemetryData.(map[string]interface{}),
		Type:        "status_update",
		CreatedAt:   time.Now(),
	}

	result := w.db.Create(&telemetry)
	if result.Error != nil {
		log.Printf("❌ Failed to store telemetry: %v", result.Error)
		return
	}


	w.cacheTelemetry(telemetry)

	log.Printf("📊 Stored telemetry for device %s", deviceID)
}

func (w *Worker) Close() {
	if w.channel != nil {
		w.channel.Close()
	}
	if w.rabbitmq != nil {
		w.rabbitmq.Close()
	}
	if w.redis != nil {
		w.redis.Close()
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func generateUUID() string {
	return uuid.New().String()
} 