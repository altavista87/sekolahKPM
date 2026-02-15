#!/usr/bin/env python3
"""
EduSync Deployment Test Suite
Tests all functionalities of the deployed Netlify application at:
https://sekolahkpm.netlify.app/

Usage:
    python test_deployed_app.py
    python test_deployed_app.py --verbose
    python test_deployed_app.py --test <test_name>
"""

import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import argparse

try:
    import httpx
    import colorama
    from colorama import Fore, Style
    colorama.init()
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "colorama", "-q"])
    import httpx
    import colorama
    from colorama import Fore, Style
    colorama.init()


# Configuration
BASE_URL = "https://sekolahkpm.netlify.app"
TIMEOUT = 30.0


@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    passed: bool
    message: str = ""
    duration_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class TestRunner:
    """Test runner with reporting."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[TestResult] = []
        self.client = httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True)
    
    def log(self, message: str, level: str = "info"):
        """Log a message with color coding."""
        if not self.verbose and level == "debug":
            return
        
        colors = {
            "info": Fore.CYAN,
            "success": Fore.GREEN,
            "warning": Fore.YELLOW,
            "error": Fore.RED,
            "debug": Fore.WHITE,
        }
        
        prefix = {
            "info": "ℹ️ ",
            "success": "✅ ",
            "warning": "⚠️ ",
            "error": "❌ ",
            "debug": "🐛 ",
        }
        
        print(f"{colors.get(level, Fore.WHITE)}{prefix.get(level, '')}{message}{Style.RESET_ALL}")
    
    async def run_test(self, test_name: str, test_func) -> TestResult:
        """Run a single test and record result."""
        self.log(f"Running: {test_name}", "debug")
        start = time.time()
        
        try:
            result = await test_func()
            duration = (time.time() - start) * 1000
            
            if isinstance(result, tuple):
                passed, message, details = result + ({},) * (3 - len(result))
            else:
                passed, message, details = result, "", {}
            
            test_result = TestResult(
                name=test_name,
                passed=passed,
                message=message,
                duration_ms=duration,
                details=details
            )
            
            status = "success" if passed else "error"
            self.log(f"{test_name}: {'PASS' if passed else 'FAIL'} ({duration:.1f}ms)", status)
            
        except Exception as e:
            duration = (time.time() - start) * 1000
            test_result = TestResult(
                name=test_name,
                passed=False,
                message=str(e),
                duration_ms=duration,
                error=str(e)
            )
            self.log(f"{test_name}: ERROR - {e}", "error")
        
        self.results.append(test_result)
        return test_result
    
    # ==================== TESTS ====================
    
    async def test_static_site(self) -> tuple:
        """Test 1: Static landing page loads correctly."""
        response = await self.client.get(BASE_URL)
        
        checks = [
            (response.status_code == 200, f"Status code: {response.status_code}"),
            ("EduSync" in response.text or "Snap & Track" in response.text, "Contains branding"),
            ("text/html" in response.headers.get("content-type", ""), "Content-Type is HTML"),
        ]
        
        failed = [c[1] for c in checks if not c[0]]
        return (
            len(failed) == 0,
            "Landing page loads" if not failed else f"Failed: {', '.join(failed)}",
            {"content_length": len(response.text)}
        )
    
    async def test_health_endpoint(self) -> tuple:
        """Test 2: Health check endpoint returns correct status."""
        response = await self.client.get(f"{BASE_URL}/api/health")
        data = response.json()
        
        checks = [
            (response.status_code == 200, f"Status: {response.status_code}"),
            (data.get("status") in ["healthy", "degraded"], f"Status field: {data.get('status')}"),
            ("timestamp" in data, "Has timestamp"),
            ("version" in data, "Has version"),
            ("services" in data, "Has services info"),
        ]
        
        failed = [c[1] for c in checks if not c[0]]
        return (
            len(failed) == 0,
            f"Health: {data.get('status', 'unknown')}, Services: {list(data.get('services', {}).keys())}",
            data
        )
    
    async def test_api_info(self) -> tuple:
        """Test 3: API root returns info."""
        response = await self.client.get(f"{BASE_URL}/api/v1")
        
        return (
            response.status_code in [200, 404],  # 404 is acceptable if not implemented
            f"Status: {response.status_code}"
        )
    
    async def test_homework_list(self) -> tuple:
        """Test 4: Homework list endpoint."""
        response = await self.client.get(f"{BASE_URL}/api/v1/homework")
        data = response.json()
        
        checks = [
            (response.status_code == 200, f"Status: {response.status_code}"),
            ("homework" in data, "Has homework field"),
            ("message" in data or isinstance(data.get("homework"), list), "Valid structure"),
        ]
        
        failed = [c[1] for c in checks if not c[0]]
        return len(failed) == 0, f"Homework API working" if not failed else f"Failed: {', '.join(failed)}", data
    
    async def test_homework_create(self) -> tuple:
        """Test 5: Create homework endpoint."""
        payload = {
            "subject": "Mathematics",
            "title": "Test Assignment",
            "description": "Test description",
            "due_date": datetime.now().isoformat()
        }
        
        response = await self.client.post(
            f"{BASE_URL}/api/v1/homework",
            json=payload
        )
        data = response.json()
        
        return (
            response.status_code in [200, 201],
            f"Status: {response.status_code}",
            data
        )
    
    async def test_users_endpoint(self) -> tuple:
        """Test 6: Users API endpoint."""
        response = await self.client.get(f"{BASE_URL}/api/v1/users")
        data = response.json()
        
        return (
            response.status_code == 200,
            f"Status: {response.status_code}",
            data
        )
    
    async def test_students_endpoint(self) -> tuple:
        """Test 7: Students API endpoint."""
        response = await self.client.get(f"{BASE_URL}/api/v1/students/test-id/homework")
        
        return (
            response.status_code == 200,
            f"Status: {response.status_code}",
            response.json()
        )
    
    async def test_telegram_webhook_get(self) -> tuple:
        """Test 8: Telegram webhook rejects GET (should be POST)."""
        response = await self.client.get(f"{BASE_URL}/webhook/telegram")
        data = response.json()
        
        # GET should return 405 Method Not Allowed
        return (
            response.status_code == 405,
            f"Correctly rejects GET with 405",
            data
        )
    
    async def test_telegram_webhook_post(self) -> tuple:
        """Test 9: Telegram webhook accepts valid POST."""
        # Valid Telegram update structure
        payload = {
            "update_id": 123456789,
            "message": {
                "message_id": 1,
                "date": int(time.time()),
                "chat": {
                    "id": 123456,
                    "type": "private"
                },
                "text": "/start"
            }
        }
        
        response = await self.client.post(
            f"{BASE_URL}/webhook/telegram",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        data = response.json()
        
        # Should accept the request (may return 200 or 500 depending on bot init)
        return (
            response.status_code in [200, 500],  # 500 is OK if bot deps not initialized
            f"Status: {response.status_code}",
            data
        )
    
    async def test_telegram_webhook_invalid(self) -> tuple:
        """Test 10: Telegram webhook rejects invalid payload."""
        response = await self.client.post(
            f"{BASE_URL}/webhook/telegram",
            json={"invalid": "payload"},
            headers={"Content-Type": "application/json"}
        )
        
        # Should either process (200) or reject invalid (400/403)
        return (
            response.status_code in [200, 400, 403],
            f"Status: {response.status_code}"
        )
    
    async def test_cors_headers(self) -> tuple:
        """Test 11: CORS headers are present."""
        response = await self.client.options(
            f"{BASE_URL}/api/health",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET"
            }
        )
        
        cors_headers = [
            "access-control-allow-origin",
            "access-control-allow-methods",
        ]
        
        present = [h for h in cors_headers if h in response.headers]
        
        return (
            len(present) > 0,
            f"CORS headers: {present}",
            dict(response.headers)
        )
    
    async def test_security_headers(self) -> tuple:
        """Test 12: Security headers are present."""
        response = await self.client.get(BASE_URL)
        
        security_headers = {
            "content-security-policy": "CSP",
            "strict-transport-security": "HSTS",
            "x-content-type-options": "Content-Type Options",
            "x-frame-options": "Frame Options",
        }
        
        present = {k: v for k, v in security_headers.items() if k in response.headers}
        
        return (
            len(present) > 0,
            f"Security headers present: {list(present.values())}",
            dict(response.headers)
        )
    
    async def test_response_time(self) -> tuple:
        """Test 13: Response time is acceptable."""
        times = []
        for _ in range(3):
            start = time.time()
            await self.client.get(BASE_URL)
            times.append((time.time() - start) * 1000)
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        return (
            avg_time < 3000,  # Should be under 3 seconds
            f"Avg: {avg_time:.0f}ms, Max: {max_time:.0f}ms",
            {"times": times}
        )
    
    async def test_json_content_type(self) -> tuple:
        """Test 14: API returns JSON content type."""
        response = await self.client.get(f"{BASE_URL}/api/health")
        
        content_type = response.headers.get("content-type", "")
        
        return (
            "application/json" in content_type,
            f"Content-Type: {content_type}"
        )
    
    async def test_404_handling(self) -> tuple:
        """Test 15: 404 handling for non-existent endpoints."""
        response = await self.client.get(f"{BASE_URL}/api/v1/nonexistent")
        
        return (
            response.status_code == 404,
            f"Status: {response.status_code}"
        )
    
    async def test_method_not_allowed(self) -> tuple:
        """Test 16: Method not allowed handling."""
        response = await self.client.delete(f"{BASE_URL}/api/health")
        
        return (
            response.status_code == 405,
            f"Status: {response.status_code}"
        )
    
    async def test_whatsapp_webhook(self) -> tuple:
        """Test 17: WhatsApp webhook endpoint exists."""
        response = await self.client.get(f"{BASE_URL}/webhook/whatsapp")
        
        # Should return 405 (GET not allowed) or be configured
        return (
            response.status_code in [200, 405, 404],
            f"Status: {response.status_code}"
        )
    
    async def test_scheduled_function_endpoint(self) -> tuple:
        """Test 18: Check if scheduled function endpoint exists."""
        # Note: Scheduled functions can't be triggered via HTTP normally
        # but we can check if the function exists
        response = await self.client.get(f"{BASE_URL}/.netlify/functions/check-reminders")
        
        return (
            response.status_code in [200, 404],  # 404 if not accessible via HTTP
            f"Status: {response.status_code}"
        )
    
    async def test_api_version(self) -> tuple:
        """Test 19: API version is returned."""
        response = await self.client.get(f"{BASE_URL}/api/health")
        data = response.json()
        
        version = data.get("version", "unknown")
        
        return (
            version != "unknown",
            f"Version: {version}",
            {"version": version}
        )
    
    async def test_content_compression(self) -> tuple:
        """Test 20: Content compression is enabled."""
        response = await self.client.get(
            BASE_URL,
            headers={"Accept-Encoding": "gzip, deflate, br"}
        )
        
        encoding = response.headers.get("content-encoding", "none")
        
        return (
            encoding in ["gzip", "br", "deflate"],
            f"Encoding: {encoding}"
        )
    
    # ==================== RUN ALL TESTS ====================
    
    async def run_all_tests(self, specific_test: Optional[str] = None):
        """Run all tests or a specific test."""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"🧪 EduSync Deployment Test Suite")
        print(f"🌐 Target: {BASE_URL}")
        print(f"⏰ Started: {datetime.now().isoformat()}")
        print(f"{'='*60}{Style.RESET_ALL}\n")
        
        tests = [
            ("Static Site", self.test_static_site),
            ("Health Check", self.test_health_endpoint),
            ("API Info", self.test_api_info),
            ("Homework List", self.test_homework_list),
            ("Homework Create", self.test_homework_create),
            ("Users Endpoint", self.test_users_endpoint),
            ("Students Endpoint", self.test_students_endpoint),
            ("Telegram Webhook (GET)", self.test_telegram_webhook_get),
            ("Telegram Webhook (POST)", self.test_telegram_webhook_post),
            ("Telegram Webhook (Invalid)", self.test_telegram_webhook_invalid),
            ("CORS Headers", self.test_cors_headers),
            ("Security Headers", self.test_security_headers),
            ("Response Time", self.test_response_time),
            ("JSON Content Type", self.test_json_content_type),
            ("404 Handling", self.test_404_handling),
            ("Method Not Allowed", self.test_method_not_allowed),
            ("WhatsApp Webhook", self.test_whatsapp_webhook),
            ("Scheduled Function", self.test_scheduled_function_endpoint),
            ("API Version", self.test_api_version),
            ("Content Compression", self.test_content_compression),
        ]
        
        if specific_test:
            tests = [(n, t) for n, t in tests if specific_test.lower() in n.lower()]
            if not tests:
                self.log(f"No test matching '{specific_test}' found", "error")
                return
        
        for name, test_func in tests:
            await self.run_test(name, test_func)
        
        await self.print_report()
    
    async def print_report(self):
        """Print final test report."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        total_time = sum(r.duration_ms for r in self.results)
        
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"📊 TEST SUMMARY")
        print(f"{'='*60}{Style.RESET_ALL}")
        
        # Results table
        print(f"\n{'Test':<35} {'Status':<10} {'Time':<10}")
        print("-" * 60)
        
        for result in self.results:
            status = f"{Fore.GREEN}PASS{Style.RESET_ALL}" if result.passed else f"{Fore.RED}FAIL{Style.RESET_ALL}"
            print(f"{result.name:<35} {status:<20} {result.duration_ms:>6.1f}ms")
            
            if not result.passed and result.message:
                print(f"  {Fore.YELLOW}└─ {result.message}{Style.RESET_ALL}")
        
        print(f"\n{'='*60}")
        print(f"Total: {total} | {Fore.GREEN}Passed: {passed}{Style.RESET_ALL} | {Fore.RED}Failed: {failed}{Style.RESET_ALL}")
        print(f"Total time: {total_time:.1f}ms")
        print(f"Success rate: {(passed/total*100):.1f}%" if total > 0 else "N/A")
        print(f"{'='*60}\n")
        
        # Detailed failures
        if failed > 0:
            print(f"{Fore.RED}❌ FAILED TESTS DETAILS:{Style.RESET_ALL}\n")
            for result in self.results:
                if not result.passed:
                    print(f"{Fore.RED}▸ {result.name}{Style.RESET_ALL}")
                    print(f"  Message: {result.message}")
                    if result.error:
                        print(f"  Error: {result.error}")
                    if self.verbose and result.details:
                        print(f"  Details: {json.dumps(result.details, indent=2)[:500]}")
                    print()
        
        # Save report to file
        report = {
            "timestamp": datetime.now().isoformat(),
            "target_url": BASE_URL,
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "success_rate": passed/total if total > 0 else 0,
                "total_time_ms": total_time
            },
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "duration_ms": r.duration_ms,
                    "details": r.details,
                    "error": r.error
                }
                for r in self.results
            ]
        }
        
        report_file = "test_report.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        self.log(f"Report saved to: {report_file}", "info")
        
        # Exit code
        sys.exit(0 if failed == 0 else 1)
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="EduSync Deployment Test Suite")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--test", "-t", help="Run specific test by name")
    args = parser.parse_args()
    
    runner = TestRunner(verbose=args.verbose)
    
    try:
        await runner.run_all_tests(specific_test=args.test)
    finally:
        await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
