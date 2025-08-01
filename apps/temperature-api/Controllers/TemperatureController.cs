using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using temperature_api.Models;

namespace temperature_api.Controllers
{
    [ApiVersion("1")]
    [Route("api/v{api-version:apiVersion}/")]
    [ApiController]
    public class SensorsController : ControllerBase
    {

        [HttpGet]
        [Route("temperature")]
        public IActionResult GetLocationTemperature(string sensorId, string location)
        {
            if (location == "")
            {
                location = sensorId switch
                {
                    "1" => "Living Room",
                    "2" => "Bedroom",
                    "3" => "Kitchen",
                    _ => "Unknown"
                };
            }

            if (sensorId == "")
            {
                sensorId = location switch
                {
                    "Living Room" => "1",
                    "Bedroom" => "2",
                    "Kitchen" => "3",
                    _ => "0"
                };
            }

            if (string.IsNullOrEmpty(sensorId)
                && string.IsNullOrEmpty(location))
            {
                return BadRequest();
            }

            var rnd = new Random();
            var temp =(double)rnd.Next(0, 40);

            var data = new TemperatureData(){
                Value = temp,
                Location = location,
                SensorID = sensorId,
                Description=$"temperature sensor at {location}"
                };

            return Ok(data);
        }
    }
}
