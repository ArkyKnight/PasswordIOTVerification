const express = require("express");
const mqtt = require("mqtt");
const cors = require("cors");

const app = express();
app.use(cors());
app.use(express.json());

let logs = [];
let pinHashStored = "81dc9bdb52d04dc20036dbd8313ed055"; // hash de 1234

const client = mqtt.connect("mqtt://broker.hivemq.com:1883");


client.on("connect", () => {
  client.subscribe("lock/attempts");
  console.log("MQTT conectado");
});

client.on("message", (topic, message) => {
  const data = JSON.parse(message.toString());
  const now = new Date().toISOString();

  let result = "deny";
  if (data.pin_hash === pinHashStored) result = "allow";

  logs.push({ time: now, pin: data.pin_hash, result });

  client.publish("lock/responses", result);
});

app.get("/logs", (req, res) => {
  res.json(logs);
});

app.post("/pin", (req, res) => {
  pinHashStored = req.body.pin_hash;
  res.json({ ok: true });
});

app.listen(3000, () => console.log("Servidor en puerto 3000"));
