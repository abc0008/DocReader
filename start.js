const { spawn } = require('child_process');
const path = require('path');

console.log('Starting backend process...');
const backendProcess = spawn('node', ['start-backend.js'], {
  stdio: 'inherit',
  env: { ...process.env, PORT: '8080' }
});

backendProcess.on('error', (err) => {
  console.error('Failed to start backend process:', err);
});

backendProcess.on('exit', (code, signal) => {
  if (code) console.log(`Backend process exited with code ${code}`);
  if (signal) console.log(`Backend process killed with signal ${signal}`);
});

console.log('Starting frontend process...');
const frontendPath = path.join(__dirname, 'frontend');
const frontendProcess = spawn('npm', ['start'], {
  cwd: frontendPath,
  stdio: 'inherit',
  env: { ...process.env, PORT: '8000' }
});

// Handle process termination
process.on('SIGINT', () => {
  backendProcess.kill('SIGINT');
  frontendProcess.kill('SIGINT');
  process.exit();
});