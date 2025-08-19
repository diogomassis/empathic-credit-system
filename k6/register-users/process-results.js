import fs from 'fs';
import readline from 'readline';

const resultsInputFile = '../results.json';
const usersOutputFile = '../users.json';
const createdUsers = [];

console.log(`Reading the k6 results file: ${resultsInputFile}...`);

const rl = readline.createInterface({
    input: fs.createReadStream(resultsInputFile),
    crlfDelay: Infinity,
});

rl.on('line', (line) => {
    try {
        const data = JSON.parse(line);
        if (data.type === 'Point' && data.metric === 'created_users') {
            const userDataFromTags = data.data.tags;
            
            if (userDataFromTags && userDataFromTags.email && userDataFromTags.password) {
                createdUsers.push({
                    id: userDataFromTags.userId,
                    email: userDataFromTags.email,
                    password_sent: userDataFromTags.password,
                    created_at: userDataFromTags.createdAt
                });
            }
        }
    } catch (e) {
        console.error('Error processing JSON line:', e);
    }
});

rl.on('close', () => {
    if (createdUsers.length > 0) {
        fs.writeFileSync(usersOutputFile, JSON.stringify(createdUsers, null, 2));
        console.log(`\nSuccess!`);
        console.log(`${createdUsers.length} users were saved to ${usersOutputFile}`);
    } else {
        console.log('\nNo users were successfully created during the test.');
    }

    fs.unlink(resultsInputFile, (err) => {
        if (err) {
            console.error(`Error removing the file ${resultsInputFile}:`, err);
        } else {
            console.log(`File ${resultsInputFile} successfully removed.`);
        }
    });
});
