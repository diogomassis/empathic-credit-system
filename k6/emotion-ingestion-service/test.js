import http from 'k6/http';
import { check } from 'k6';
import { Trend } from 'k6/metrics';
import { SharedArray } from 'k6/data';

const users = new SharedArray('users', function () {
  return JSON.parse(open('../users.json')); 
});

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
    const url = 'http://localhost:9999/v1/emotions/stream';
    const randomUser = users[Math.floor(Math.random() * users.length)];
    if (!randomUser) {
        return; 
    }

    const payload = JSON.stringify({
        userId: randomUser.id,
        timestamp: new Date().toISOString(),
        emotionEvent: {
            type: 'SENTIMENT_ANALYSIS',
            metrics: {
                positivity: Math.random(),
                intensity: Math.random(),
                stress_level: Math.random(),
            },
        },
    });

    const params = {
        headers: {
            'Content-Type': 'application/json',
            'X-Request-ID': `k6-${__VU}-${__ITER}`,
            'X-Internal-Key': 'your-different-secret-for-internal-services'
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