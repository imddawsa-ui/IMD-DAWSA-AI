const json = (data, status = 200, extra = {}) => new Response(JSON.stringify(data), {
  status, headers: { "content-type": "application/json; charset=utf-8", "x-content-type-options": "nosniff", "cache-control": "no-store", ...extra }
});
const cors = (request, env) => {
  const origin = request.headers.get("Origin") || "";
  const allowed = (env.CORS_ORIGINS || "").split(",").map(x => x.trim()).filter(Boolean);
  const headers = { "access-control-allow-methods": "GET,POST,PATCH,PUT,DELETE,OPTIONS", "access-control-allow-headers": "Authorization,Content-Type", "vary": "Origin" };
  if (allowed.includes(origin)) headers["access-control-allow-origin"] = origin;
  return headers;
};
export default {
 async fetch(request, env) {
  const headers = cors(request, env);
  if (request.method === "OPTIONS") return new Response(null, {status:204,headers});
  const url = new URL(request.url);
  if (url.pathname === "/api/health" && request.method === "GET") {
   return json({ok:true,app:"IMD DAWSA AI API",version:"0.1.0",runtime:"cloudflare-workers",database:!!env.DB},200,headers);
  }
  if (url.pathname === "/api/readiness" && request.method === "GET") {
   try {
    const row = await env.DB.prepare("SELECT 1 AS ready").first();
    return json({ready:!!row,checks:{database:!!row,ai_provider:false},note:"AI provider is not configured on this Worker yet."},200,headers);
   } catch (error) {
    return json({ready:false,checks:{database:false},error:"Database unavailable"},503,headers);
   }
  }
  if (url.pathname.startsWith("/api/")) return json({error:"This API module is not deployed yet.",code:"MODULE_NOT_IMPLEMENTED"},501,headers);
  return json({error:"Not found"},404,headers);
 }
};
