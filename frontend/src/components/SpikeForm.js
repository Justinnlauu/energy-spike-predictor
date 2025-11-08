import React, { useState } from "react";
import axios from "axios";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";

const SpikeForm = () => {
  const [formData, setFormData] = useState({
    outdoor_temp_C: 22, outdoor_humidity_pct: 45, dew_point_C: 10,
    solar_irradiance_Wm2: 300, wind_speed_mps: 3, forecast_temp_next1h: 23,
    forecast_humidity_next1h: 47, shift_id: 1, hour_of_day: 8, day_of_week: 1,
    maintenance_flag: 0, post_maintenance_startup: 0,
    cleanroom_occupancy_count: 12, cleanroom_temp_C: 22, cleanroom_humidity_pct: 45,
    temp_diff_C: 0, humidity_diff_pct: 0, hvac_fan_speed_pct: 70, chiller_load_pct: 65,
    autoclave_cycle_active: 1, compressor_count_running: 2
  });

  const [prediction, setPrediction] = useState(null);
  const [history, setHistory] = useState([]);

  const handleChange = (e) => {
    setFormData({...formData, [e.target.name]: parseFloat(e.target.value)});
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await axios.post("http://127.0.0.1:8000/predict_spike", formData);
      setPrediction(res.data);
      setHistory(prev => [...prev, {time: new Date().toLocaleTimeString(), probability: res.data.probability}]);
    } catch (err) {
      console.error(err);
    }
  }

  return (
    <div className="p-4">
      <h2 className="text-xl font-bold mb-2">Energy Spike Predictor</h2>
      <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-2">
        {Object.keys(formData).map(key => (
          <div key={key}>
            <label className="block text-sm">{key}</label>
            <input
              type="number"
              step="any"
              name={key}
              value={formData[key]}
              onChange={handleChange}
              className="border p-1 w-full"
            />
          </div>
        ))}
      </form>
      <button onClick={handleSubmit} className="mt-2 p-2 bg-blue-500 text-white rounded">Predict Spike</button>
      
      {prediction && (
        <div className="mt-4 p-2 border">
          <p>Spike Prediction: {prediction.spike_prediction ? "Yes" : "No"}</p>
          <p>Probability: {(prediction.probability*100).toFixed(2)}%</p>
        </div>
      )}

      <div className="mt-4">
        <h3 className="font-bold mb-2">Prediction Probability History</h3>
        <LineChart width={600} height={300} data={history}>
          <CartesianGrid strokeDasharray="3 3"/>
          <XAxis dataKey="time"/>
          <YAxis domain={[0,1]}/>
          <Tooltip/>
          <Line type="monotone" dataKey="probability" stroke="#8884d8" />
        </LineChart>
      </div>
    </div>
  );
}

export default SpikeForm;
