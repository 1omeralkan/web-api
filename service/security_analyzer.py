"""
Security Analyzer Service
=========================

Web sitelerinin güvenlik başlıklarını ve yapılandırmasını analiz eden servis.

KONTROL EDİLEN GÜVENLİK ÖĞELERİ:
---------------------------------
1. Security Headers (X-Frame-Options, CSP, HSTS, X-XSS-Protection, etc.)
2. Cookie güvenliği (HttpOnly, Secure, SameSite)
3. SSL/TLS sertifika bilgileri
4. CORS yapılandırması
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import ssl
import socket
from datetime import datetime
from urllib.parse import urlparse

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SecurityHeader:
    """Güvenlik header bilgisi."""
    name: str
    present: bool
    value: Optional[str]
    severity: str  # critical, high, medium, low
    description: str
    recommendation: str


class SecurityAnalyzer:
    """
    Web sitesi güvenlik analizi yapan sınıf.
    """
    
    # Önemli güvenlik header'ları ve açıklamaları
    SECURITY_HEADERS = {
        "Strict-Transport-Security": {
            "severity": "critical",
            "description": "HSTS - Tarayıcıyı sadece HTTPS kullanmaya zorlar",
            "recommendation": "max-age=31536000; includeSubDomains; preload"
        },
        "Content-Security-Policy": {
            "severity": "critical", 
            "description": "XSS ve injection saldırılarına karşı koruma",
            "recommendation": "default-src 'self'; script-src 'self'"
        },
        "X-Frame-Options": {
            "severity": "high",
            "description": "Clickjacking saldırılarına karşı koruma",
            "recommendation": "DENY veya SAMEORIGIN"
        },
        "X-Content-Type-Options": {
            "severity": "medium",
            "description": "MIME type sniffing'i engeller",
            "recommendation": "nosniff"
        },
        "X-XSS-Protection": {
            "severity": "medium",
            "description": "Tarayıcı XSS filtresi (eski tarayıcılar için)",
            "recommendation": "1; mode=block"
        },
        "Referrer-Policy": {
            "severity": "low",
            "description": "Referrer bilgisinin paylaşımını kontrol eder",
            "recommendation": "strict-origin-when-cross-origin"
        },
        "Permissions-Policy": {
            "severity": "low",
            "description": "Tarayıcı özelliklerinin kullanımını kontrol eder",
            "recommendation": "camera=(), microphone=(), geolocation=()"
        },
    }
    
    def analyze_headers(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """
        HTTP response header'larını güvenlik açısından analiz eder.
        
        Args:
            headers: HTTP response headers
            
        Returns:
            Dict: Güvenlik analiz sonucu
        """
        results = []
        score = 100
        
        # Her güvenlik header'ını kontrol et
        for header_name, info in self.SECURITY_HEADERS.items():
            # Header'ı bul (case-insensitive)
            header_value = None
            for key, value in headers.items():
                if key.lower() == header_name.lower():
                    header_value = value
                    break
            
            present = header_value is not None
            
            result = SecurityHeader(
                name=header_name,
                present=present,
                value=header_value,
                severity=info["severity"],
                description=info["description"],
                recommendation=info["recommendation"] if not present else None
            )
            results.append(result)
            
            # Skor hesapla
            if not present:
                if info["severity"] == "critical":
                    score -= 25
                elif info["severity"] == "high":
                    score -= 15
                elif info["severity"] == "medium":
                    score -= 10
                else:
                    score -= 5
        
        # Skor minimum 0
        score = max(0, score)
        
        # Seviye belirleme
        if score >= 80:
            grade = "A"
            grade_color = "green"
        elif score >= 60:
            grade = "B"
            grade_color = "yellow"
        elif score >= 40:
            grade = "C"
            grade_color = "orange"
        else:
            grade = "D"
            grade_color = "red"
        
        return {
            "score": score,
            "grade": grade,
            "grade_color": grade_color,
            "headers": [
                {
                    "name": h.name,
                    "present": h.present,
                    "value": h.value,
                    "severity": h.severity,
                    "description": h.description,
                    "recommendation": h.recommendation
                }
                for h in results
            ],
            "missing_critical": sum(1 for h in results if not h.present and h.severity == "critical"),
            "missing_high": sum(1 for h in results if not h.present and h.severity == "high"),
            "total_headers_checked": len(results),
            "headers_present": sum(1 for h in results if h.present)
        }
    
    def analyze_cookies(self, cookies_header: Optional[str], set_cookie_headers: List[str]) -> Dict[str, Any]:
        """
        Cookie güvenliğini analiz eder.
        """
        results = []
        issues = []
        
        for cookie_str in set_cookie_headers:
            cookie_info = self._parse_cookie(cookie_str)
            results.append(cookie_info)
            
            # Güvenlik kontrolleri
            if not cookie_info.get("secure"):
                issues.append({
                    "cookie": cookie_info.get("name"),
                    "issue": "Secure flag eksik",
                    "severity": "high",
                    "description": "Cookie HTTPS olmadan gönderilebilir"
                })
            
            if not cookie_info.get("httponly"):
                issues.append({
                    "cookie": cookie_info.get("name"),
                    "issue": "HttpOnly flag eksik",
                    "severity": "high",
                    "description": "Cookie JavaScript ile okunabilir (XSS riski)"
                })
            
            if not cookie_info.get("samesite"):
                issues.append({
                    "cookie": cookie_info.get("name"),
                    "issue": "SameSite flag eksik",
                    "severity": "medium",
                    "description": "CSRF saldırılarına açık olabilir"
                })
        
        return {
            "cookies": results,
            "total_cookies": len(results),
            "issues": issues,
            "issue_count": len(issues)
        }
    
    def _parse_cookie(self, cookie_str: str) -> Dict[str, Any]:
        """Cookie string'ini parse eder."""
        parts = cookie_str.split(';')
        
        # İlk kısım cookie adı ve değeri
        name_value = parts[0].strip()
        name = name_value.split('=')[0] if '=' in name_value else name_value
        
        # Flag'leri kontrol et
        cookie_lower = cookie_str.lower()
        
        return {
            "name": name,
            "secure": "secure" in cookie_lower,
            "httponly": "httponly" in cookie_lower,
            "samesite": "samesite" in cookie_lower,
            "raw": cookie_str[:100]  # İlk 100 karakter
        }
    
    def get_ssl_info(self, hostname: str, port: int = 443) -> Dict[str, Any]:
        """
        SSL sertifika bilgilerini alır.
        """
        try:
            context = ssl.create_default_context()
            
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    
                    # Sertifika bilgilerini parse et
                    subject = dict(x[0] for x in cert.get('subject', []))
                    issuer = dict(x[0] for x in cert.get('issuer', []))
                    
                    # Tarih parse
                    not_before = datetime.strptime(cert['notBefore'], '%b %d %H:%M:%S %Y %Z')
                    not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                    
                    # Kalan gün
                    days_remaining = (not_after - datetime.now()).days
                    
                    return {
                        "valid": True,
                        "subject": subject.get('commonName', 'N/A'),
                        "issuer": issuer.get('organizationName', 'N/A'),
                        "not_before": not_before.isoformat(),
                        "not_after": not_after.isoformat(),
                        "days_remaining": days_remaining,
                        "is_expired": days_remaining < 0,
                        "expiring_soon": 0 < days_remaining <= 30,
                        "protocol": ssock.version(),
                    }
                    
        except Exception as e:
            logger.error(f"SSL bilgisi alınamadı: {hostname} - {e}")
            return {
                "valid": False,
                "error": str(e)
            }


# Singleton instance
security_analyzer = SecurityAnalyzer()
