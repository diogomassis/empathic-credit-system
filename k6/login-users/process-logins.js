import fs from 'fs';
import readline from 'readline';

const resultsInputFile = '../results-login.json';
const sessionsOutputFile = '../sessions.json';
const successfulSessions = [];

console.log(`Reading the k6 results file: ${resultsInputFile}...`);

if (!fs.existsSync(resultsInputFile)) {
  console.error(`\nError: Input file "${resultsInputFile}" not found.`);
  console.error('Did you run the login test with "k6 run --out json=results-login.json ..."?');
  process.exit(1);
}

const rl = readline.createInterface({
  input: fs.createReadStream(resultsInputFile),
  crlfDelay: Infinity,
});

rl.on('line', (line) => {
  try {
  const data = JSON.parse(line);
  if (data.type === 'Point' && data.metric === 'successful_logins') {
    const sessionData = data.data.tags;
    if (sessionData && sessionData.token) {
    successfulSessions.push({
      userId: sessionData.userId,
      email: sessionData.email,
      token: sessionData.token
    });
    }
  }
  } catch (e) {
  }
});

rl.on('close', () => {
  if (successfulSessions.length > 0) {
    fs.writeFileSync(sessionsOutputFile, JSON.stringify(successfulSessions, null, 2));
    console.log(`\nSuccess!`);
    console.log(`${successfulSessions.length} user sessions were saved to ${sessionsOutputFile}`);
  } else {
    console.log('\nNo successful logins were performed during the test.');
  }
  fs.unlink(resultsInputFile, (err) => {
    if (err) {
      console.error(`Error removing the file ${resultsInputFile}:`, err);
    } else {
      console.log(`File ${resultsInputFile} successfully removed.`);
    }
  });
});
