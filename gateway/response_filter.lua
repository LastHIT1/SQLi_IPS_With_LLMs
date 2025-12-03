-- Response Filter - Checks response for SQL error patterns
-- Redis status check happens in access phase (set by access_filter.lua)

local SQL_ERROR_PATTERNS = {
    "programmingerror",
    "psycopg2",
    "syntax error at or near",
    "relation .* does not exist",
    "column .* does not exist",
    "unterminated quoted string",
    "invalid input syntax",
    "operationalerror",
    "databaseerror",
    "dataerror",
    "integrityerror",
    "exception value:",
    "exception type:",
    "you have an error in your sql syntax",
    "unknown column",
    "no such table",
    "no such column",
}

local function render_error_page(pattern)
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
        .pattern-box{background:#1a1a2e;color:#ff6b6b;padding:1rem;border-radius:8px;font-family:monospace;word-break:break-all}
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
                <div style="font-size:3.5rem">&#128737;&#65039;</div>
                <h2 class="mt-2">Security Alert</h2>
                <p class="mb-0">Response blocked by SQL Error Filter</p>
            </div>
            <div class="card-body p-4">
                <div class="alert alert-danger"><strong>SQL Error Detected!</strong> The response contained sensitive database error information.</div>
                <h6 class="mb-3" style="color:var(--fiu-blue)">Threat Analysis</h6>
                <div class="detail">
                    <div class="detail-label">Detection Type</div>
                    <div>SQL Error in Response</div>
                </div>
                <div class="mb-4">
                    <div class="detail-label mb-2">Pattern Matched</div>
                    <div class="pattern-box">]] .. pattern .. [[</div>
                </div>
                <div class="detail">
                    <div class="detail-label">Action Taken</div>
                    <div>Response blocked to prevent information leakage</div>
                </div>
                <div class="text-center mt-4">
                    <a href="/" class="btn btn-gold">Return to BookStore</a>
                </div>
            </div>
        </div>
    </div>
    <footer class="footer-fiu"><small>FIU BookStore - Protected by Response Filter</small></footer>
</body>
</html>]]
end

local function find_sql_error(content)
    if not content or content == "" then
        return nil
    end
    local lower = content:lower()
    for _, pattern in ipairs(SQL_ERROR_PATTERNS) do
        if lower:find(pattern, 1, true) or lower:match(pattern) then
            return pattern
        end
    end
    return nil
end

-- Main body filter logic
local chunk = ngx.arg[1]
local eof = ngx.arg[2]
local ctx = ngx.ctx

-- Skip if filter is disabled (checked in access phase)
if ctx.sql_filter_disabled then
    return
end

-- Only process HTML responses
local content_type = ngx.header["Content-Type"] or ""
if not content_type:find("text/html") then
    return
end

-- Initialize buffer
if not ctx.response_body then
    ctx.response_body = ""
end

-- Accumulate chunks
if chunk then
    ctx.response_body = ctx.response_body .. chunk
end

-- On final chunk, check for SQL errors
if eof then
    local matched_pattern = find_sql_error(ctx.response_body)
    if ctx.response_body ~= "" and matched_pattern then
        -- Replace with error page showing the matched pattern
        ngx.arg[1] = render_error_page(matched_pattern)
        ngx.header["Content-Length"] = nil
    else
        -- Pass through original
        ngx.arg[1] = ctx.response_body
    end
else
    -- Buffer chunks, don't output yet
    ngx.arg[1] = nil
end
