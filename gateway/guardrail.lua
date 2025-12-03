local http = require "resty.http"
local cjson = require "cjson.safe"
local redis = require "resty.redis"

local GUARDRAIL_URL = "http://guardrail:5000/"
local TIMEOUT_MS = 10000
local SQL_ERROR_FILTER_KEY = "sql_error_filter_status"

-- Check SQL error filter status from Redis
local function check_sql_filter_status()
    local red = redis:new()
    red:set_timeout(100)

    local ok, err = red:connect("cache", 6379)
    if not ok then
        return false  -- Default to enabled
    end

    local res, err = red:get(SQL_ERROR_FILTER_KEY)
    red:set_keepalive(10000, 100)

    if res and res ~= ngx.null and res == "0" then
        return true  -- Disabled
    end
    return false  -- Enabled
end

local HTML_ESCAPE_MAP = {
    ["&"] = "&amp;",
    ["<"] = "&lt;",
    [">"] = "&gt;",
    ['"'] = "&quot;",
    ["'"] = "&#39;",
}

local function escape_html(str)
    if not str then return "" end
    return tostring(str):gsub("[&<>\"']", HTML_ESCAPE_MAP)
end

local function render_403(threat_type, payload, url, method)
    return [[<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Alert | FIU BookStore</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root{--fiu-blue:#081E3F;--fiu-gold:#B6862C;--danger:#dc3545}
        body{background:#f5f5f5;min-height:100vh;display:flex;flex-direction:column}
        .navbar-fiu{background:var(--fiu-blue)!important}
        .card-danger{background:linear-gradient(135deg,var(--danger),#b02a37);color:#fff;padding:2rem;text-align:center}
        .detail{background:#f8f9fa;border-left:4px solid var(--danger);padding:1rem;margin-bottom:1rem;border-radius:0 8px 8px 0}
        .detail-label{font-weight:600;color:var(--fiu-blue);font-size:.85rem;text-transform:uppercase}
        .payload-box{background:#1a1a2e;color:#ff6b6b;padding:1rem;border-radius:8px;font-family:monospace;word-break:break-all}
        .btn-gold{background:var(--fiu-gold);border-color:var(--fiu-gold);color:#fff}
        .btn-gold:hover{background:#C9A227;color:#fff}
        .footer-fiu{background:var(--fiu-blue);color:#fff;padding:1rem;text-align:center;margin-top:auto}
    </style>
</head>
<body>
    <nav class="navbar navbar-dark navbar-fiu">
        <div class="container-fluid">
            <a class="navbar-brand fw-bold" href="/">FIU BookStore</a>
        </div>
    </nav>
    <div class="container py-5 flex-grow-1">
        <div class="card shadow mx-auto" style="max-width:650px">
            <div class="card-danger">
                <div style="font-size:3.5rem">🛡️</div>
                <h2 class="mt-2">Security Alert</h2>
                <p class="mb-0">Request blocked by Guardrail</p>
            </div>
            <div class="card-body p-4">
                <div class="alert alert-danger"><strong>Attack detected!</strong> This incident has been logged.</div>
                <h6 class="mb-3" style="color:var(--fiu-blue)">Threat Analysis</h6>
                <div class="detail">
                    <div class="detail-label">Threat Type</div>
                    <div>]] .. escape_html(threat_type) .. [[</div>
                </div>
                <div class="detail">
                    <div class="detail-label">Target</div>
                    <div>]] .. escape_html(method) .. " " .. escape_html(url) .. [[</div>
                </div>
                <div class="mb-4">
                    <div class="detail-label mb-2">Payload</div>
                    <div class="payload-box">]] .. escape_html(payload) .. [[</div>
                </div>
                <div class="text-center">
                    <a href="/" class="btn btn-gold">Return to BookStore</a>
                </div>
            </div>
        </div>
    </div>
    <footer class="footer-fiu"><small>FIU BookStore - Protected by Guardrail</small></footer>
</body>
</html>]]
end

-- Main logic
local uri = ngx.var.request_uri

-- Check SQL error filter status and store in context for body_filter
ngx.ctx.sql_filter_disabled = check_sql_filter_status()

-- Skip static files early
if uri:sub(1, 8) == "/static/" then
    return
end

ngx.req.read_body()

local method = ngx.var.request_method
local body = ngx.req.get_body_data()
local content_type = ngx.req.get_headers()["content-type"]

local httpc = http.new()
httpc:set_timeout(TIMEOUT_MS)

local res, err = httpc:request_uri(GUARDRAIL_URL, {
    method = "POST",
    body = body,
    headers = {
        ["Content-Type"] = content_type,
        ["X-Original-URI"] = uri,
        ["X-Original-Method"] = method,
    },
    keepalive_timeout = 60000,
    keepalive_pool = 10,
})

if not res then
    ngx.log(ngx.ERR, "Guardrail error: ", err)
    return
end

if res.status ~= 403 then
    return
end

local data = cjson.decode(res.body) or {}
ngx.status = ngx.HTTP_FORBIDDEN
ngx.header["Content-Type"] = "text/html; charset=utf-8"
ngx.say(render_403(
    data.threat_type or "SQL Injection Attempt",
    data.payload or "Not identified",
    data.target_url or uri,
    data.method or method
))
return ngx.exit(ngx.HTTP_OK)
