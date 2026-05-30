'use strict';
// Preload: Kein direkter Node-Zugriff aus dem Renderer nötig
// Die App kommuniziert nur über HTTP mit dem lokalen Express-Backend
const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('trainconnect', {
  version: '1.7.0',
  platform: process.platform,
});
