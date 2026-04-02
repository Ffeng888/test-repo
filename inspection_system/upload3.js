const {execSync} = require('child_process');
const fs = require('fs');
const path = require('path');

const PREFIX = 'inspection_system/';
const SKIP_PATTERNS = ['.onnx', '.pt', '.jpg', '.png', '.opencode'];

function uploadFile(filePath, repoPath) {
  // Skip large binary files
  for (const pattern of SKIP_PATTERNS) {
    if (filePath.includes(pattern)) {
      return 'SKIP: ' + repoPath + ' (binary)';
    }
  }
  
  const content = fs.readFileSync(filePath);
  const base64 = Buffer.from(content).toString('base64');
  
  try {
    let sha = null;
    try {
      const existing = JSON.parse(execSync('gh api repos/FengKequanX/test-repo/contents/' + repoPath, {encoding: 'utf8'}));
      sha = existing.sha;
    } catch(e) {}

    let cmd = 'gh api -X PUT repos/FengKequanX/test-repo/contents/' + repoPath + ' -f message="Add ' + repoPath + '" -f content="' + base64 + '"';
    if (sha) cmd += ' -f sha="' + sha + '"';
    
    execSync(cmd, {encoding: 'utf8'});
    return 'OK: ' + repoPath;
  } catch(e) {
    return 'ERR: ' + repoPath + ' - ' + e.message.split('\n')[0];
  }
}

function walkDir(dir, baseDir) {
  const items = fs.readdirSync(dir);
  for (const item of items) {
    if (item === '.git') continue;
    const fullPath = path.join(dir, item);
    const stat = fs.statSync(fullPath);
    
    if (stat.isDirectory()) {
      walkDir(fullPath, baseDir);
    } else {
      const repoPath = PREFIX + path.relative(baseDir, fullPath).replace(/\\/g, '/');
      console.log(uploadFile(fullPath, repoPath));
    }
  }
}

walkDir('.', '.');
console.log('\nDone! (Binary files skipped)');