// verify-fix.js
// Run this script with Node.js 18+ to verify the proxy fix.
// Usage: node verify-fix.js

const PROXY_URL = 'http://localhost:3000/api/proxy/health';

async function verify() {
  console.log(`Testing Proxy at: ${PROXY_URL}`);
  
  try {
    const res = await fetch(PROXY_URL);
    const contentType = res.headers.get('content-type');
    
    console.log(`Status: ${res.status} ${res.statusText}`);
    
    let body;
    try {
      body = await res.json();
    } catch (e) {
      body = await res.text();
    }

    if (res.status === 200) {
      console.log('✅ SUCCESS: Backend is ONLINE. Proxy is forwarding correctly.');
      console.log('Response:', JSON.stringify(body, null, 2));
    } else if (res.status === 503) {
      console.log('✅ SUCCESS (Backend Offline): Proxy returned 503 as expected.');
      console.log('Error Payload:', JSON.stringify(body, null, 2));
    } else {
      console.log(`❌ UNEXPECTED STATUS: ${res.status}`);
      console.log('Body:', body);
    }

  } catch (error) {
    console.error('❌ CONNECTION ERROR: Could not connect to Next.js proxy.');
    console.error('Ensure the frontend is running on http://localhost:3000');
  }
}

verify();