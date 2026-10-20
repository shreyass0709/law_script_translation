// Forward /api/* to the FastAPI server, so the browser never needs CORS.
const API_URL = process.env.API_URL || "http://127.0.0.1:8000";

export default {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/:path*` }];
  },
};
