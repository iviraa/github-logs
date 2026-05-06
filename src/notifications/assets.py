"""Inline assets embedded in outgoing emails via MIME `cid:` references."""

from __future__ import annotations

import base64

# 32x32 GitHub mark, originally from github.githubassets.com/favicons/favicon.png.
# Inlined here so emails render the logo without remote-image fetches and without
# data: URIs (Gmail strips those).
_GITHUB_LOGO_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAACXBIWXMAAAsTAAALEwEAmpwY"
    "AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAANTSURBVHgBvVeNTdtAFH7vbCilUpt"
    "uYFQihUhNzQQJEzSZoGSChgkIEwATNJ0AmICM4ISKWCKoHiGtVDUCn1/v2cRx4nNIcNRPgp"
    "zvnd/fvT8jLAnLsgrGVqEOQlaR0AYECwgKIRFhpNYeITkQYFeOf195njdahi8+K7hUsgzca"
    "CPi51jgElDKdGTweOK5rgcvUYAtNl+/PVbLFuSBoDP/j3Hiec5oaQUiqzevFdGCNYAAPEkP"
    "BzpviPmNYrlsr1M4g3kxz2KxbGtoU6zb8nnoPBF7IIzyOeH8gvp/Gf2uCJUZRNRRK2e6FXn"
    "CsuxCSgEOuJTlBO3h4KZxP+jvKGbNWBFOu5AxdeO/aO9JMBwOb/vv792bJlBwNKsXWOYbeZ"
    "x4jlxv4ubPlBG+2L+7c2ILLFtpPh4XslLLKtkWjGGUjHjeMzFI8fbpYYf5mPzAea5j+GjAT"
    "Op4Tsg4s8B4ruPBkjDEBnuhKdgqBPyiPQSyBjlhZgS0qqZ1jgVhjGVddyCMWDC6kBP+FjgZ"
    "QaxKu6wLFQU10GvQXsWlWeBrQwqaeqqoClXjP+lIciyuYE0Yuj+mWZIACrI5Da15Arssq3b"
    "ngAdpQZZYpcPlApHOoIKA/wVEraFCezdhZbbX6xkCW7M7Yg94uvPGtqzCmrBbsmtaAoInKI"
    "CelkY5B5EECOWhdj9AR0TNRKtCbXevkluJ4l7la1alZdlCbhmXujh4wuluuXIMOYSrlD7Lo"
    "nOtCbvhh71KRy0iLQlOwukW8HTSnrkuKFedEYne0HW6sEho0bbBDKqEcJgReJEYws6922s+"
    "teNpywzrtqQjuW10zYfgOs0EL4eDXkPHdLf88UJdeB2WgE9ih0t9WAd4oQSfh+yVPmjgN+7"
    "7fiAaqUZC8jyTa0DZtCQLJWvSZ+JCJF+JdkIYj2ctPiRJHPALPF4p5VphXc/AIlpCuCf/iv"
    "bkeW4otdXMFsRzIfq+mohuHVgBKnNooXBlULLLpr4LeCwPyLyIA1B94QhCJyDxS2Dw7m7QP"
    "3+JAmEgo2goe2YMyvgwmfVEEsNBH1dVQGf5BNpmxAd5EuaUhJzg+FF3vp813CzshkO33+Z0"
    "UUy+w7LgohaO5tjhd5UhrbXMFtwdeXx/9py6vlU66T98qp4a9HCubgAAAABJRU5ErkJggg=="
)

GITHUB_LOGO_PNG: bytes = base64.b64decode(_GITHUB_LOGO_PNG_B64)
GITHUB_LOGO_CID: str = "github-logo"
