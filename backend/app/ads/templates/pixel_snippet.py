"""Meta Pixel snippet generator with server-side event forwarding."""


def generate_pixel_snippet(pixel_id: str, api_base_url: str) -> str:
    """Generate a Meta Pixel JavaScript snippet with CAPI forwarding.

    The snippet:
    1. Loads the Meta Pixel base code
    2. Tracks PageView
    3. Sends server-side events to our backend for Conversion API
    """
    return f"""<!-- Meta Pixel Code -->
<script>
!function(f,b,e,v,n,t,s)
{{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)}};
if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];
s.parentNode.insertBefore(t,s)}}(window, document,'script',
'https://connect.facebook.net/en_US/fbevents.js');
fbq('init', '{pixel_id}');
fbq('track', 'PageView');

// Server-side event forwarding to Conversion API
(function() {{
  var apiBase = '{api_base_url}';

  function sendServerEvent(eventName, customData) {{
    var payload = {{
      event_name: eventName,
      event_time: new Date().toISOString(),
      source_url: window.location.href,
      fbc: getCookie('_fbc') || null,
      fbp: getCookie('_fbp') || null,
      user_data: {{
        client_ip: null,
        client_user_agent: navigator.userAgent
      }},
      custom_data: customData || null
    }};

    fetch(apiBase + '/api/v1/ads/conversions', {{
      method: 'POST',
      headers: {{
        'Content-Type': 'application/json',
        'X-Tenant-ID': getMeta('tenant-id') || 'default'
      }},
      body: JSON.stringify(payload),
      keepalive: true
    }}).catch(function() {{}});
  }}

  function getCookie(name) {{
    var match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? match[2] : null;
  }}

  function getMeta(name) {{
    var el = document.querySelector('meta[name="' + name + '"]');
    return el ? el.getAttribute('content') : null;
  }}

  window._go4TrackEvent = sendServerEvent;

  sendServerEvent('PageView');
}})();
</script>
<noscript><img height="1" width="1" style="display:none"
  src="https://www.facebook.com/tr?id={pixel_id}&ev=PageView&noscript=1"
/></noscript>
<!-- End Meta Pixel Code -->"""
