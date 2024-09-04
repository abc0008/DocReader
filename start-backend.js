const { spawn } = require('child_process');
const path = require('path');

const backendPath = path.join(__dirname, 'backend');

console.log('Current working directory:', process.cwd());
console.log('Backend path:', backendPath);

const pythonCommand = 'python3';  // Use python3 for MacOS

console.log(`Attempting to start backend server using command: ${pythonCommand}`);
console.log('Backend will be started on port 8080');

const backend = spawn(pythonCommand, ['app.py'], {
  cwd: backendPath,
  env: { 
    ...process.env, 
    FLASK_APP: 'app.py', 
    FLASK_ENV: 'development',
    FLASK_DEBUG: 'True',
    PYTHONUNBUFFERED: '1',
    PORT: '8080'
  },
  stdio: 'inherit'
});

backend.on('error', (err) => {
  console.error('Failed to start backend:', err);
  console.error('Error details:', err.message);
  if (err.code === 'ENOENT') {
    console.error('The specified file or command was not found. Make sure Python 3 is installed and in your PATH.');
  }
});

backend.on('exit', (code, signal) => {
  if (code) console.log(`Backend process exited with code ${code}`);
  if (signal) console.log(`Backend process killed with signal ${signal}`);
});

console.log('Backend process spawned. Check above logs for any startup issues.');