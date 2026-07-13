import axios from 'axios';
import { signPayload, getFingerprint, hashBody, solvePoW } from './crypto.js';
import { useStore } from '../store/state.js';

const api = axios.create({
    baseURL: '/api'
});

function uuidv4() {
    return "10000000-1000-4000-8000-100000000000".replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
}

// Global request interceptor to inject cryptographic headers
api.interceptors.request.use(async (config) => {
    const store = useStore();

    let bodyBytes;
    if (config.data instanceof Blob) {
        // Raw binary payload (e.g. media uploads) - hash the exact bytes being sent,
        // so the signature covers the real file content instead of a stand-in.
        bodyBytes = new Uint8Array(await config.data.arrayBuffer());
    } else if (config.data instanceof ArrayBuffer) {
        bodyBytes = new Uint8Array(config.data);
    } else if (config.data) {
        bodyBytes = JSON.stringify(config.data);
    } else {
        bodyBytes = new Uint8Array();
    }

    const bodyHash = await hashBody(bodyBytes);
    const timestamp = Math.floor(Date.now() / 1000).toString();
    const nonce = uuidv4();
    const fingerprint = await getFingerprint();

    config.headers['X-Fingerprint'] = fingerprint;

    // Attach signature if logged in
    if (store.state.keyPair && store.state.userId) {
        const method = config.method.toUpperCase();

        // The signature must cover EXACTLY what the server sees via request.url.path
        // and request.url.query. config.url may already carry its own query string
        // (e.g. '/feed?requires=x'), so split on '?' by hand instead of re-parsing
        // through URL/URLSearchParams, which can silently re-encode characters
        // (e.g. spaces as '+') and desync the signature from the actual bytes sent.
        const rawUrl = config.url || '';
        const qIndex = rawUrl.indexOf('?');
        const urlPath = qIndex === -1 ? rawUrl : rawUrl.slice(0, qIndex);
        let queryStr = qIndex === -1 ? '' : rawUrl.slice(qIndex + 1);

        if (config.params) {
            const paramsStr = new URLSearchParams(config.params).toString();
            queryStr = queryStr ? `${queryStr}&${paramsStr}` : paramsStr;
        }

        // Always derive the signed path from baseURL - never assume config.url
        // already contains the '/api' prefix the routers are mounted under.
        const path = `${config.baseURL || ''}${urlPath}`;

        const canonicalPayload = `${method}\n${path}\n${queryStr}\n${timestamp}\n${nonce}\n${bodyHash}`;

        const signatureBase64 = await signPayload(store.state.keyPair.privateKey, canonicalPayload);

        config.headers['X-User-Id'] = store.state.userId;
        config.headers['X-Timestamp'] = timestamp;
        config.headers['X-Nonce'] = nonce;
        config.headers['X-Signature'] = signatureBase64;
    }

    return config;
}, error => Promise.reject(error));


// Global response interceptor to handle auto-logout on cascade ban or key rotation
api.interceptors.response.use(response => response, error => {
    if (error.response && [401, 403].includes(error.response.status)) {
        const store = useStore();
        if (store.state.isRegistered) {
            store.logout();
            store.addToast(error.response.status === 403 ? "Account Restricted" : "Session Expired", "bi-exclamation-triangle");
        }
    }
    return Promise.reject(error);
});

export async function apiWithPoW(method, url, data) {
    // 1. Fetch Challenge
    const challengeRes = await api.get('/security/challenge');
    const { challenge_id, difficulty } = challengeRes.data;

    // 2. Solve PoW
    const powNonce = await solvePoW(challenge_id, difficulty);

    // 3. Execute original request with headers
    return api({
        method,
        url,
        data,
        headers: {
            'X-Challenge-Id': challenge_id,
            'X-Pow-Nonce': powNonce
        }
    });
}

export default api;