from __future__ import annotations

import json

from poc.evidence.redactor import REDACTED, REDACTED_PATH, redact_value, redacted_json_dumps


def test_synthetic_nested_secret_corpus_is_removed_before_serialization() -> None:
    secrets = {
        "authorization": "synthetic-auth-value-001",
        "bearer": "synthetic-bearer-value-002",
        "api_header": "synthetic-x-api-key-value-003",
        "provider_key": "synthetic-provider-key-value-004",
        "shaped_api_key": "sk-proj-SYNTHETICKEYVALUE123456789",
        "cookie": "synthetic-cookie-value-006",
        "set_cookie": "synthetic-set-cookie-value-007",
        "query": "synthetic-query-token-value-008",
        "github": "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "windows_path": r"C:\Users\phase1-synthetic-user\private\credential.txt",
        "posix_path": "/home/phase1-synthetic-user/private/credential.txt",
        "nested": "synthetic-nested-error-secret-012",
        "relayrouter_key": "synthetic-relayrouter-key-value-013",
    }
    corpus = {
        "headers": {
            "Authorization": f"Bearer {secrets['authorization']}",
            "x-api-key": secrets["api_header"],
            "Cookie": f"session={secrets['cookie']}",
            "Set-Cookie": f"auth={secrets['set_cookie']}; HttpOnly",
        },
        "environment": {
            "A6API_KEY": secrets["provider_key"],
            "RELAYROUTER_API_KEY": secrets["relayrouter_key"],
        },
        "api_key_text": secrets["shaped_api_key"],
        "urls": [f"https://provider.invalid/v1?access_token={secrets['query']}&mode=test"],
        "github_token": secrets["github"],
        "private_paths": [secrets["windows_path"], secrets["posix_path"]],
        "errors": [
            {
                "type": "SyntheticTransportError",
                "message": f"request failed with Bearer {secrets['bearer']} at {secrets['windows_path']}",
                    "details": {"message": f"nested diagnostic secret: {secrets['nested']}"},
                "url": f"https://provider.invalid/failure?api_key={secrets['query']}",
            },
            f"Authorization: {secrets['authorization']}; x-api-key={secrets['api_header']}",
        ],
    }

    sanitized = redact_value(corpus)
    serialized = json.dumps(sanitized, sort_keys=True, ensure_ascii=True)
    direct_serialized = redacted_json_dumps(corpus)

    leaked_items = [
        name
        for name, secret in secrets.items()
        if secret in serialized or secret in direct_serialized
    ]
    assert leaked_items == []
    assert REDACTED in serialized
    assert REDACTED_PATH in serialized
    assert direct_serialized == redacted_json_dumps(corpus)
