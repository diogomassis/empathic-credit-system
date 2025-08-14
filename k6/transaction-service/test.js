import http from 'k6/http';
import { check } from 'k6';
import { Trend } from 'k6/metrics';
import { uuidv4 } from "https://jslib.k6.io/k6-utils/1.4.0/index.js";

const emotionEventDuration = new Trend('emotion_event_duration');

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
    const url = 'http://localhost:8888/v1/transactions';

    const payload = JSON.stringify({
        userId: uuidv4(),
        amount: 19.90
    });

    const params = {
        headers: {
            'Content-Type': 'application/json',
            'X-Request-ID': `k6-${__VU}-${__ITER}`,
        },
    };

    const start = Date.now();
    const res = http.post(url, payload, params);
    const end = Date.now();
    const duration = end - start;

    check(res, {
        'status is 202 (Accepted)': (r) => r.status === 202,
    });

    emotionEventDuration.add(duration);
}
