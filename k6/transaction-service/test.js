import http from 'k6/http';
import { check } from 'k6';
import { Trend } from 'k6/metrics';
import { SharedArray } from 'k6/data';
// import { uuidv4 } from "https://jslib.k6.io/k6-utils/1.4.0/index.js";

const sessions = new SharedArray('sessions', function () {
  return JSON.parse(open('../sessions.json')); 
});

const transactionEventDuration = new Trend('transaction_event_duration');

export const options = {
    stages: [
        { duration: '15s', target: 10 },
        { duration: '30s', target: 10 },
        { duration: '10s', target: 0 },
    ],
    thresholds: {
        http_req_duration: ['p(95)<500'],
        http_req_failed: ['rate<0.01'],
    },
};

export default function () {
    const url = 'http://localhost:9999/v1/transactions';
    const randomSession = sessions[Math.floor(Math.random() * sessions.length)];
    if (!randomSession) {
        return; 
    }
    const payload = JSON.stringify({
        userId: randomSession.userId,
        amount: +(Math.random() * (50000 - 1) + 1).toFixed(2)
    });

    const params = {
        headers: {
            'Content-Type': 'application/json',
            'X-Request-ID': `k6-${__VU}-${__ITER}`,
            'Authorization': `Bearer ${randomSession.token}`
        },
    };

    const start = Date.now();
    const res = http.post(url, payload, params);
    const end = Date.now();
    const duration = end - start;

    check(res, {
        'status is 202 (Accepted)': (r) => r.status === 202,
    });

    transactionEventDuration.add(duration);
}
