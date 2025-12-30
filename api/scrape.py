from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
import re
import ssl

# Chatbot signatures to detect
CHATBOT_SIGNATURES = {
    "Intercom": ["intercom", "widget.intercom.io", "intercom-container"],
    "Drift": ["drift", "js.driftt.com", "drift-widget"],
    "Zendesk": ["zendesk", "zopim", "zdassets", "zopim.com"],
    "HubSpot": ["hubspot", "js.hs-scripts.com", "hbspt", "hs-banner"],
    "Freshchat": ["freshchat", "wchat.freshchat.com", "freshworks"],
    "Tidio": ["tidio", "code.tidio.co", "tidiochat"],
    "Crisp": ["crisp.chat", "client.crisp.chat", "crisp-client"],
    "Tawk.to": ["tawk.to", "embed.tawk.to", "tawkto"],
    "LiveChat": ["livechat", "cdn.livechatinc.com", "livechatinc"],
    "Olark": ["olark", "static.olark.com"],
    "Chatra": ["chatra", "call.chatra.io"],
    "JivoChat": ["jivosite", "jivochat", "code.jivosite.com"],
    "Comm100": ["comm100", "livechat.comm100.com"],
    "Pure Chat": ["purechat", "app.purechat.com"],
    "Smartsupp": ["smartsupp", "smartsuppchat"],
    "Kayako": ["kayako", "kayakocdn"],
    "Help Scout": ["helpscout", "beacon-v2.helpscout.net"],
    "Gorgias": ["gorgias", "config.gorgias.chat"],
    "Chatlio": ["chatlio", "chatlio.com"],
    "SnapEngage": ["snapengage", "snapengage.com"],
}


def fetch_website(url):
    """Fetch website HTML"""
    if not url.startswith("http"):
        url = "https://" + url
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    
    # Create SSL context that doesn't verify (for simplicity)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url, headers=headers)
    
    with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
        return response.read().decode("utf-8", errors="ignore")


def extract_text(html):
    """Extract visible text from HTML"""
    # Remove script and style content
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<noscript[^>]*>.*?</noscript>", "", html, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", html)
    
    # Clean up whitespace
    text = re.sub(r"\s+", " ", text).strip()
    
    # Limit text length
    return text[:10000] if len(text) > 10000 else text


def extract_scripts(html):
    """Extract all script sources"""
    scripts = []
    
    # Find script src attributes
    src_matches = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
    scripts.extend(src_matches)
    
    # Find inline script content (first 200 chars of each)
    inline_matches = re.findall(r"<script[^>]*>(.*?)</script>", html, re.DOTALL | re.IGNORECASE)
    for match in inline_matches:
        if match.strip():
            scripts.append(f"[inline]: {match.strip()[:200]}")
    
    return scripts[:50]  # Limit to 50 scripts


def extract_meta(html):
    """Extract meta information"""
    meta = {}
    
    # Title
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if title_match:
        meta["title"] = title_match.group(1).strip()
    
    # Meta description
    desc_match = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if not desc_match:
        desc_match = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']', html, re.IGNORECASE)
    if desc_match:
        meta["description"] = desc_match.group(1).strip()
    
    return meta


def detect_chatbots(html):
    """Detect chatbot integrations"""
    html_lower = html.lower()
    detected = []
    
    for provider, patterns in CHATBOT_SIGNATURES.items():
        for pattern in patterns:
            if pattern.lower() in html_lower:
                detected.append({
                    "provider": provider,
                    "matched_pattern": pattern
                })
                break  # Only add each provider once
    
    return detected


def detect_other_integrations(html):
    """Detect other common integrations"""
    html_lower = html.lower()
    integrations = []
    
    other_tools = {
        "Google Analytics": ["google-analytics.com", "gtag", "googletagmanager", "ga.js", "analytics.js"],
        "Google Tag Manager": ["googletagmanager.com/gtm"],
        "Facebook Pixel": ["connect.facebook.net", "fbq(", "facebook-pixel"],
        "Hotjar": ["hotjar", "static.hotjar.com"],
        "Segment": ["segment.com/analytics", "analytics.segment.com"],
        "Mixpanel": ["mixpanel", "cdn.mxpnl.com"],
        "Amplitude": ["amplitude.com", "cdn.amplitude.com"],
        "Heap": ["heap-analytics", "heapanalytics.com"],
        "FullStory": ["fullstory", "edge.fullstory.com"],
        "Clarity": ["clarity.ms"],
        "Sentry": ["sentry.io", "browser.sentry-cdn.com"],
        "Stripe": ["js.stripe.com", "stripe.com"],
        "PayPal": ["paypal.com/sdk"],
        "Shopify": ["cdn.shopify.com"],
        "WordPress": ["wp-content", "wp-includes"],
        "Webflow": ["webflow.com"],
        "Wix": ["wix.com", "parastorage.com"],
        "Squarespace": ["squarespace.com", "static1.squarespace.com"],
    }
    
    for tool, patterns in other_tools.items():
        for pattern in patterns:
            if pattern.lower() in html_lower:
                integrations.append(tool)
                break
    
    return integrations


def scrape_website(url):
    """Main scraping function"""
    try:
        html = fetch_website(url)
        
        return {
            "success": True,
            "url": url,
            "meta": extract_meta(html),
            "text_content": extract_text(html),
            "scripts": extract_scripts(html),
            "chatbots": detect_chatbots(html),
            "has_chatbot": len(detect_chatbots(html)) > 0,
            "other_integrations": detect_other_integrations(html),
            "html_length": len(html)
        }
        
    except Exception as e:
        return {
            "success": False,
            "url": url,
            "error": str(e)
        }


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Parse query parameters
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        
        url = params.get("url", [None])[0]
        
        if not url:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "Missing 'url' parameter",
                "usage": "?url=https://example.com"
            }).encode())
            return
        
        # Scrape the website
        result = scrape_website(url)
        
        self.send_response(200 if result["success"] else 500)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(result, indent=2).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
