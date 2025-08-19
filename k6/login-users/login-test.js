import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter } from 'k6/metrics';
import { SharedArray } from 'k6/data';
const successfulLogins = new Counter('successful_logins');

const users = new SharedArray('users', function () {
  try {
    return JSON.parse(open('../users.json'));
  } catch (e) {
    return [];
  }
});

export const options = {
  stages: [
    { duration: '30s', target: 20 }, 
    { duration: '1m', target: 20 },  
    { duration: '10s', target: 0 },  
  ],
  thresholds: {
    'http_req_failed': ['rate<0.01'],
  },
};

export default function () {
  if (users.length === 0) {
    console.error("The user list is empty. Cancel the test (Ctrl+C) or generate the users.json file.");
    sleep(10);
    return;
  }
  const url = 'http://localhost:9999/v1/auth/login';
  const user = users[Math.floor(Math.random() * users.length)];
  const payload = JSON.stringify({
    email: user.email,
    password: user.password_sent,
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };
  const res = http.post(url, payload, params);
  const success = check(res, {
    'status is 200 (OK)': (r) => r.status === 200,
  });

  if (success) {
    let responseData;
    try {
      responseData = res.json();
    } catch (e) {
      console.error('Failed to parse the JSON response from login.');
      return;
    }
    const token = responseData.access_token;

    if (token) {
      successfulLogins.add(1, { 
        userId: user.id, 
        email: user.email, 
        token: token 
      });
    }
  }
}