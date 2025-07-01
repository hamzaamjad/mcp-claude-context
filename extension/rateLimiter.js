/**
 * Client-side rate limiter for Chrome extension
 * Implements token bucket algorithm to respect server rate limits
 */

class RateLimiter {
  constructor(config = {}) {
    this.requestsPerSecond = config.requestsPerSecond || 3;
    this.burstSize = config.burstSize || 10;
    this.tokens = this.burstSize;
    this.lastRefill = Date.now();
    this.queue = [];
    this.processing = false;
    
    // Start token refill interval
    this.startRefillInterval();
  }
  
  startRefillInterval() {
    setInterval(() => {
      this.refillTokens();
      this.processQueue();
    }, 100); // Check every 100ms
  }
  
  refillTokens() {
    const now = Date.now();
    const elapsed = (now - this.lastRefill) / 1000; // Convert to seconds
    const tokensToAdd = elapsed * this.requestsPerSecond;
    
    this.tokens = Math.min(this.burstSize, this.tokens + tokensToAdd);
    this.lastRefill = now;
  }
  
  async acquire() {
    return new Promise((resolve) => {
      this.queue.push(resolve);
      this.processQueue();
    });
  }
  
  processQueue() {
    if (this.processing || this.queue.length === 0) return;
    
    this.processing = true;
    
    while (this.queue.length > 0 && this.tokens >= 1) {
      this.tokens -= 1;
      const resolve = this.queue.shift();
      resolve();
    }
    
    this.processing = false;
  }
  
  getStatus() {
    return {
      tokensAvailable: Math.floor(this.tokens),
      queueLength: this.queue.length,
      burstSize: this.burstSize,
      requestsPerSecond: this.requestsPerSecond
    };
  }
  
  // Check if we can make a request without waiting
  canMakeRequest() {
    return this.tokens >= 1;
  }
  
  // Get estimated wait time in milliseconds
  getWaitTime() {
    if (this.tokens >= 1) return 0;
    
    const tokensNeeded = 1 - this.tokens;
    const waitSeconds = tokensNeeded / this.requestsPerSecond;
    return Math.ceil(waitSeconds * 1000);
  }
}

// Create a shared rate limiter instance
const bridgeRateLimiter = new RateLimiter({
  requestsPerSecond: 3,
  burstSize: 10
});

// Helper function to make rate-limited fetch requests
async function rateLimitedFetch(url, options = {}) {
  // Wait for rate limit token
  await bridgeRateLimiter.acquire();
  
  try {
    const response = await fetch(url, options);
    
    // Check for rate limit headers
    const remaining = response.headers.get('X-RateLimit-Remaining');
    const limit = response.headers.get('X-RateLimit-Limit');
    
    if (remaining !== null && limit !== null) {
      console.log(`[Rate Limiter] Remaining: ${remaining}/${limit}`);
    }
    
    // Handle 429 Too Many Requests
    if (response.status === 429) {
      const retryAfter = response.headers.get('Retry-After') || '1';
      const waitTime = parseInt(retryAfter) * 1000;
      
      console.warn(`[Rate Limiter] Rate limit hit, waiting ${waitTime}ms`);
      await new Promise(resolve => setTimeout(resolve, waitTime));
      
      // Retry the request
      return rateLimitedFetch(url, options);
    }
    
    return response;
  } catch (error) {
    console.error('[Rate Limiter] Request failed:', error);
    throw error;
  }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { RateLimiter, bridgeRateLimiter, rateLimitedFetch };
}