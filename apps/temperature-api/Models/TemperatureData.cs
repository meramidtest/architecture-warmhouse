namespace temperature_api.Models
{
    public class TemperatureData
    {
        public double Value { get; set; }
        public string Unit { get; set; } = "°C";
        public DateTime Timestamp { get; set; } = DateTime.Now;
        public string Location { get; set; }
        public string Status { get; set; } = "active";
        public string SensorID { get; set; }
        public string SensorType { get; set; } = "temperature";
        public string Description { get; set; }

    }
}
