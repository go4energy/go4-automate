"""Broadcaster module manifest."""

manifest = {
    "name": "broadcaster",
    "label": "Broadcaster",
    "version": "1.0.0",
    "description": "Audio-Briefings erstellen, Channels verwalten, Listener tracken.",
    "icon": "M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z",
    "color": "#0EA5E9",
    "category": "marketing",
    "application": True,
    "depends": [],
    "has_frontend": True,
    "has_models": True,
    "has_config_schema": True,
    "routers": ["router", "listener_router"],
    "router_prefix": "/broadcaster",
    "sidebar": {"group": "MARKETING", "order": 35},
    "frontend": {
        "base_route": "/broadcaster",
        "routes": [
            {
                "path": "",
                "name": "broadcaster",
                "view": "BroadcasterView",
                "meta": {"title": "Broadcaster"},
            },
            {
                "path": "channels/new",
                "name": "broadcaster-channel-new",
                "view": "BroadcasterChannelEditView",
                "meta": {"title": "Neuer Channel", "parent": "broadcaster"},
            },
            {
                "path": "channels/:id",
                "name": "broadcaster-channel-detail",
                "view": "BroadcasterChannelDetailView",
                "props": True,
                "meta": {"title": "Channel Detail", "parent": "broadcaster"},
            },
            {
                "path": "channels/:id/edit",
                "name": "broadcaster-channel-edit",
                "view": "BroadcasterChannelEditView",
                "props": True,
                "meta": {"title": "Channel bearbeiten", "parent": "broadcaster"},
            },
        ],
    },
}
