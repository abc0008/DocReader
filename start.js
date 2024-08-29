const { spawn } = require('child_process');
const path = require('path');

// Start backend
const backendProcess = spawn('node', ['start-backend.js'], {
  stdio: 'inherit'
});

// Start frontend
const frontendPath = path.join(__dirname, 'frontend');
const frontendProcess = spawn('npm', ['start'], {
  cwd: frontendPath,
  stdio: 'inherit'
});

// Handle process termination
process.on('SIGINT', () => {
  backendProcess.kill('SIGINT');
  frontendProcess.kill('SIGINT');
  process.exit();
});