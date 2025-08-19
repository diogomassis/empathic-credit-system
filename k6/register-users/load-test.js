import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter } from 'k6/metrics';
import { uuidv4 } from "https://jslib.k6.io/k6-utils/1.4.0/index.js";

const createdUserCounter = new Counter('created_users');

export const options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '1m', target: 10 },
    { duration: '10s', target: 0 },
  ],
  thresholds: {
    'http_req_failed': ['rate<0.1'],
  },
};

export default function () {
  const endpoint = 'http://localhost:9999/v1/auth/register';

  const uuid = uuidv4();
  const password = `pass_${uuid}`;
  const email = `user_${uuid}@gmail.com`;

  const payload = JSON.stringify({
    email: email,
    password: password,
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const res = http.post(endpoint, payload, params);

  const success = check(res, {
    'status is 200 (Created)': (r) => r.status === 200,
  });

  if (success) {
    let createdUserResponse = null;
    try {
      createdUserResponse = res.json();
    } catch (e) {
      console.error("Failed to parse JSON response.");
      createdUserResponse = {};
    }
    createdUserCounter.add(1, { 
      email: email, 
      password: password,
      userId: createdUserResponse.id || 'N/A',
      createdAt: createdUserResponse.created_at || 'N/A'
    });
  }
  sleep(1);
}
