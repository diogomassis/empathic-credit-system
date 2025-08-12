import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend } from 'k6/metrics';

const emotionEventDuration = new Trend('emotion_event_duration');

function uuidv4() {
    // https://stackoverflow.com/a/2117523/2715716
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

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

    const payload = JSON.stringify({
        userId: uuidv4(),
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
