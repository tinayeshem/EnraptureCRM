"""
Thorough API POST Methods Test Script for Enrapture CRM
========================================================
Tests all 8 POST endpoints defined in `main.py`:
  1. POST /customer
  2. POST /booking
  3. POST /room-booking
  4. POST /camp-booking
  5. POST /catering
  6. POST /shuttle-booking
  7. POST /review
  8. POST /boat-booking

Includes:
  - Happy Path / End-to-end relational flow
  - Negative and Edge Case testing (409 Conflict, 404 Not Found, 422 Validation errors)
  - Automatic test data cleanup in Supabase
  - Standalone execution with CLI arguments (--url, --verbose, --no-cleanup, --fail-fast)
  - Seamless in-process execution via FastAPI TestClient OR against a live server URL
  - Pytest compatibility
"""

import sys
import os
import time
import uuid
import argparse
import warnings

# Suppress Starlette / httpx deprecation warnings
warnings.filterwarnings("ignore")

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from datetime import datetime, timezone, timedelta, date
from typing import Any, Dict, List, Optional

from fastapi.testclient import TestClient
from main import app
from database.db import supabase
import httpx


# Terminal colors for formatted reporting
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


# Enable ANSI escape sequences on Windows consoles if needed
if sys.platform == "win32":
    os.system("")


class TestResult:
    def __init__(self, name: str, endpoint: str, passed: bool, status_code: int, duration_ms: float, detail: str = ""):
        self.name = name
        self.endpoint = endpoint
        self.passed = passed
        self.status_code = status_code
        self.duration_ms = duration_ms
        self.detail = detail


class ApiClientWrapper:
    """Unifies TestClient (in-process) and httpx.Client (live server) behind one interface."""
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url.rstrip("/") if base_url else None
        if self.base_url:
            self._client = httpx.Client(base_url=self.base_url, timeout=15.0)
            self.mode = f"Live Server ({self.base_url})"
        else:
            self._client = TestClient(app)
            self.mode = "FastAPI In-Process (TestClient)"

    def post(self, path: str, json: Optional[Dict[str, Any]] = None) -> httpx.Response:
        return self._client.post(path, json=json)

    def close(self):
        if hasattr(self._client, "close"):
            self._client.close()


class PostMethodsTester:
    def __init__(self, client: ApiClientWrapper, verbose: bool = False, fail_fast: bool = False, cleanup: bool = True):
        self.client = client
        self.verbose = verbose
        self.fail_fast = fail_fast
        self.cleanup_enabled = cleanup

        self.results: List[TestResult] = []
        self.created_ids: Dict[str, List[int]] = {
            "customer": [],
            "booking": [],
            "room_booking": [],
            "camping_booking": [],
            "catering": [],
            "shuttle_booking": [],
            "review": [],
            "boat_booking": [],
        }

        # Unique tag to prevent collisions
        self.run_tag = uuid.uuid4().hex[:6]

    def log(self, text: str):
        print(text)

    def run_test(
        self,
        name: str,
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]],
        expected_status: int,
        validator: Optional[Any] = None,
    ) -> bool:
        start = time.perf_counter()
        error_detail = ""
        response = None

        try:
            response = self.client.post(endpoint, json=payload)
            duration_ms = (time.perf_counter() - start) * 1000

            status_matches = response.status_code == expected_status
            validation_passed = True
            validation_error = ""

            if status_matches and validator:
                try:
                    res_json = response.json()
                    validator_result = validator(res_json, response)
                    if validator_result is not None and not validator_result:
                        validation_passed = False
                        validation_error = "Custom assertion validator returned False."
                except Exception as ex:
                    validation_passed = False
                    validation_error = f"Validator raised exception: {str(ex)}"

            passed = status_matches and validation_passed

            if not passed:
                if not status_matches:
                    error_detail = f"Expected status {expected_status}, got {response.status_code}. Response: {response.text}"
                else:
                    error_detail = validation_error

            res = TestResult(
                name=name,
                endpoint=endpoint,
                passed=passed,
                status_code=response.status_code,
                duration_ms=duration_ms,
                detail=error_detail,
            )
            self.results.append(res)

            # Console output
            status_badge = (
                f"{Colors.GREEN}[PASS]{Colors.RESET}" if passed else f"{Colors.RED}[FAIL]{Colors.RESET}"
            )
            self.log(
                f"  {status_badge} {name:<45} {Colors.CYAN}{endpoint:<18}{Colors.RESET} "
                f"Status: {response.status_code} ({duration_ms:.1f}ms)"
            )

            if self.verbose or not passed:
                if payload:
                    self.log(f"       {Colors.DIM}Payload :{Colors.RESET} {payload}")
                self.log(f"       {Colors.DIM}Response:{Colors.RESET} {response.text}")
                if error_detail:
                    self.log(f"       {Colors.RED}Error   :{Colors.RESET} {error_detail}")

            if not passed and self.fail_fast:
                self.log(f"\n{Colors.RED}Fail-fast triggered. Aborting remaining tests.{Colors.RESET}")
                return False

            return passed

        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000
            res = TestResult(
                name=name,
                endpoint=endpoint,
                passed=False,
                status_code=-1,
                duration_ms=duration_ms,
                detail=f"Network/Execution exception: {str(e)}",
            )
            self.results.append(res)
            self.log(f"  {Colors.RED}[ERROR]{Colors.RESET} {name:<45} {Colors.CYAN}{endpoint:<18}{Colors.RESET} Exception: {e}")
            if self.fail_fast:
                return False
            return False

    def run_all(self) -> bool:
        self.log(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 75}{Colors.RESET}")
        self.log(f"{Colors.BOLD}{Colors.HEADER}  Enrapture CRM API - POST Methods Test Suite{Colors.RESET}")
        self.log(f"{Colors.DIM}  Target: {self.client.mode}{Colors.RESET}")
        self.log(f"{Colors.DIM}  Run Tag: {self.run_tag}{Colors.RESET}")
        self.log(f"{Colors.BOLD}{Colors.HEADER}{'=' * 75}{Colors.RESET}\n")

        # -------------------------------------------------------------
        # SUITE 1: Happy Path / Relational Creation Flow
        # -------------------------------------------------------------
        self.log(f"{Colors.BOLD}--- Suite 1: Happy Path & End-to-End Relational Creation ---{Colors.RESET}")

        # Shared state across sequential relational tests
        context = {
            "customer_id": None,
            "first_name": f"TestUser_{self.run_tag}",
            "last_name": f"Tester_{self.run_tag}",
            "booking_id": None,
            "room_booking_id": None,
            "camp_booking_id": None,
            "catering_order_id": None,
            "shuttle_booking_id": None,
            "review_id": None,
            "boat_booking_id": None,
        }

        # 1.1 POST /customer
        def validate_customer_create(res_json, resp):
            data = res_json.get("data", {})
            cust_id = data.get("customer_id")
            assert cust_id is not None, "Returned payload does not contain customer_id"
            assert data.get("first_name") == context["first_name"]
            assert data.get("last_name") == context["last_name"]
            context["customer_id"] = cust_id
            self.created_ids["customer"].append(cust_id)
            return True

        if not self.run_test(
            name="1.1 Create Customer (Valid)",
            method="POST",
            endpoint="/customer",
            payload={
                "first_name": context["first_name"],
                "last_name": context["last_name"],
                "email": f"test_{self.run_tag}@enrapture-test.com",
                "phone": "+27821112233",
            },
            expected_status=201,
            validator=validate_customer_create,
        ) and self.fail_fast:
            return self.finalize()

        # 1.2 POST /booking (Requires customer_id)
        def validate_booking_create(res_json, resp):
            data = res_json.get("data", {})
            b_id = data.get("booking_id")
            assert b_id is not None, "Returned payload does not contain booking_id"
            assert data.get("customer_id") == context["customer_id"]
            assert float(data.get("total_price", 0)) == 1450.00
            context["booking_id"] = b_id
            self.created_ids["booking"].append(b_id)
            return True

        if not self.run_test(
            name="1.2 Create Booking (Valid)",
            method="POST",
            endpoint="/booking",
            payload={
                "customer_id": context["customer_id"],
                "booking_status": "confirmed",
                "total_price": "1450.00",
            },
            expected_status=201,
            validator=validate_booking_create,
        ) and self.fail_fast:
            return self.finalize()

        # 1.3 POST /room-booking (Requires booking_id)
        today = date.today()
        check_in = (today + timedelta(days=7)).isoformat()
        check_out = (today + timedelta(days=10)).isoformat()

        def validate_room_booking(res_json, resp):
            data = res_json.get("data", {})
            rb_id = data.get("room_booking_id")
            assert rb_id is not None, "Returned payload does not contain room_booking_id"
            assert data.get("booking_id") == context["booking_id"]
            context["room_booking_id"] = rb_id
            self.created_ids["room_booking"].append(rb_id)
            return True

        self.run_test(
            name="1.3 Create Room Booking (Valid)",
            method="POST",
            endpoint="/room-booking",
            payload={
                "booking_id": context["booking_id"],
                "check_in_date": check_in,
                "check_out_date": check_out,
                "number_of_guests": 2,
                "room_type": "Deluxe Chalet",
            },
            expected_status=201,
            validator=validate_room_booking,
        )

        # 1.4 POST /camp-booking (Requires booking_id)
        camp_arrival = (today + timedelta(days=12)).isoformat()
        camp_departure = (today + timedelta(days=15)).isoformat()

        def validate_camp_booking(res_json, resp):
            data = res_json.get("data", {})
            cb_id = data.get("camp_booking_id")
            assert cb_id is not None, "Returned payload does not contain camp_booking_id"
            assert data.get("booking_id") == context["booking_id"]
            assert data.get("campsite_id") == 1, f"Expected default campsite_id 1, got {data.get('campsite_id')}"
            context["camp_booking_id"] = cb_id
            self.created_ids["camping_booking"].append(cb_id)
            return True

        self.run_test(
            name="1.4 Create Camp Booking (Valid, default campsite_id=1)",
            method="POST",
            endpoint="/camp-booking",
            payload={
                "booking_id": context["booking_id"],
                "arrival_date": camp_arrival,
                "departure_date": camp_departure,
                "number_of_campers": 4,
                "tent_required": True,
                "equipment_rental": True,
            },
            expected_status=201,
            validator=validate_camp_booking,
        )

        # 1.5 POST /catering
        def validate_catering(res_json, resp):
            data = res_json.get("data", {})
            cat_id = data.get("order_id")
            assert cat_id is not None, "Returned payload does not contain order_id"
            context["catering_order_id"] = cat_id
            self.created_ids["catering"].append(cat_id)
            return True

        self.run_test(
            name="1.5 Create Catering Order (Valid)",
            method="POST",
            endpoint="/catering",
            payload={
                "event_type": "Wedding Reception",
                "person_count": 85,
            },
            expected_status=201,
            validator=validate_catering,
        )

        # 1.6 POST /shuttle-booking
        def validate_shuttle_booking(res_json, resp):
            data = res_json.get("data", {})
            sb_id = data.get("shuttle_booking_id")
            assert sb_id is not None, "Returned payload does not contain shuttle_booking_id"
            context["shuttle_booking_id"] = sb_id
            self.created_ids["shuttle_booking"].append(sb_id)
            return True

        self.run_test(
            name="1.6 Create Shuttle Booking (Valid)",
            method="POST",
            endpoint="/shuttle-booking",
            payload={
                "persons_count": 4,
                "vehicle": "Mercedes Sprinter Van",
                "duration": 45,
            },
            expected_status=201,
            validator=validate_shuttle_booking,
        )

        # 1.7 POST /boat-booking (Requires booking_id)
        boat_dep = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        boat_ret = (datetime.now(timezone.utc) + timedelta(days=2, hours=3)).isoformat()

        def validate_boat_booking(res_json, resp):
            data = res_json.get("data", {})
            bb_id = data.get("boat_booking_id")
            assert bb_id is not None, "Returned payload does not contain boat_booking_id"
            assert data.get("booking_id") == context["booking_id"]
            context["boat_booking_id"] = bb_id
            self.created_ids["boat_booking"].append(bb_id)
            return True

        self.run_test(
            name="1.7 Create Boat Booking (Valid)",
            method="POST",
            endpoint="/boat-booking",
            payload={
                "booking_id": context["booking_id"],
                "departure_time": boat_dep,
                "return_time": boat_ret,
                "destination": "Sunset Lagoon",
                "number_of_passengers": 6,
                "captain_required": True,
            },
            expected_status=201,
            validator=validate_boat_booking,
        )

        # 1.8 POST /review (Requires customer_id & booking_id)
        def validate_review(res_json, resp):
            data = res_json.get("data", {})
            rev_id = data.get("review_id")
            assert rev_id is not None, "Returned payload does not contain review_id"
            assert data.get("customer_id") == context["customer_id"]
            assert data.get("booking_id") == context["booking_id"]
            assert data.get("rating") == 5
            context["review_id"] = rev_id
            self.created_ids["review"].append(rev_id)
            return True

        self.run_test(
            name="1.8 Create Review (Valid)",
            method="POST",
            endpoint="/review",
            payload={
                "customer_id": context["customer_id"],
                "booking_id": context["booking_id"],
                "rating": 5,
                "comment": "Outstanding hospitality and spotless accommodation!",
            },
            expected_status=201,
            validator=validate_review,
        )

        # -------------------------------------------------------------
        # SUITE 2: Negative and Edge Cases
        # -------------------------------------------------------------
        self.log(f"\n{Colors.BOLD}--- Suite 2: Negative and Edge Cases (Validation & Errors) ---{Colors.RESET}")

        # 2.1 Duplicate Customer (HTTP 409 Conflict)
        def validate_duplicate_conflict(res_json, resp):
            detail = res_json.get("detail", "")
            assert "already exists" in detail.lower(), f"Unexpected detail message: {detail}"
            return True

        self.run_test(
            name="2.1 Duplicate Customer -> 409 Conflict",
            method="POST",
            endpoint="/customer",
            payload={
                "first_name": context["first_name"],
                "last_name": context["last_name"],
                "email": "different_email@test.com",
            },
            expected_status=409,
            validator=validate_duplicate_conflict,
        )

        # 2.2 Customer Missing Required Field (HTTP 422)
        self.run_test(
            name="2.2 Customer Missing 'last_name' -> 422",
            method="POST",
            endpoint="/customer",
            payload={"first_name": "Incomplete"},
            expected_status=422,
        )

        # 2.3 Booking for Non-Existent Customer (HTTP 404)
        def validate_booking_not_found(res_json, resp):
            detail = res_json.get("detail", "")
            assert "does not exist" in detail.lower(), f"Unexpected detail: {detail}"
            return True

        self.run_test(
            name="2.3 Booking with Invalid customer_id -> 404",
            method="POST",
            endpoint="/booking",
            payload={
                "customer_id": 999999999,
                "booking_status": "confirmed",
                "total_price": "500.00",
            },
            expected_status=404,
            validator=validate_booking_not_found,
        )

        # 2.4 Booking Missing 'total_price' (HTTP 422)
        self.run_test(
            name="2.4 Booking Missing 'total_price' -> 422",
            method="POST",
            endpoint="/booking",
            payload={
                "customer_id": context["customer_id"],
                "booking_status": "confirmed",
            },
            expected_status=422,
        )

        # 2.5 Room Booking Invalid Date Format (HTTP 422)
        self.run_test(
            name="2.5 Room Booking Invalid Date Format -> 422",
            method="POST",
            endpoint="/room-booking",
            payload={
                "booking_id": context["booking_id"] or 1,
                "check_in_date": "not-a-valid-date",
                "check_out_date": "2026-10-10",
                "number_of_guests": 2,
            },
            expected_status=422,
        )

        # 2.6 Camp Booking Missing Required Field 'arrival_date' (HTTP 422)
        self.run_test(
            name="2.6 Camp Booking Missing arrival_date -> 422",
            method="POST",
            endpoint="/camp-booking",
            payload={
                "booking_id": context["booking_id"] or 1,
                "departure_date": "2026-11-05",
                "number_of_campers": 2,
            },
            expected_status=422,
        )

        # 2.7 Catering Missing 'event_type' (HTTP 422)
        self.run_test(
            name="2.7 Catering Missing event_type -> 422",
            method="POST",
            endpoint="/catering",
            payload={"person_count": 50},
            expected_status=422,
        )

        # 2.8 Shuttle Booking Invalid Data Type (HTTP 422)
        self.run_test(
            name="2.8 Shuttle Booking Invalid persons_count (str) -> 422",
            method="POST",
            endpoint="/shuttle-booking",
            payload={
                "persons_count": "three_people",
                "vehicle": "Van",
                "duration": 30,
            },
            expected_status=422,
        )

        # 2.9 Review Rating Out of Range (rating > 5) (HTTP 422)
        self.run_test(
            name="2.9 Review Rating > 5 (Schema Bound ge=1, le=5) -> 422",
            method="POST",
            endpoint="/review",
            payload={
                "customer_id": context["customer_id"] or 1,
                "booking_id": context["booking_id"] or 1,
                "rating": 10,
                "comment": "Too good to be 5 stars",
            },
            expected_status=422,
        )

        # 2.10 Boat Booking Invalid Datetime (HTTP 422)
        self.run_test(
            name="2.10 Boat Booking Invalid departure_time -> 422",
            method="POST",
            endpoint="/boat-booking",
            payload={
                "booking_id": context["booking_id"] or 1,
                "departure_time": "invalid_timestamp",
                "destination": "Island",
                "number_of_passengers": 2,
                "captain_required": False,
            },
            expected_status=422,
        )

        return self.finalize()

    def cleanup(self):
        """Clean up all inserted test records from Supabase in reverse dependency order."""
        if not self.cleanup_enabled:
            self.log(f"\n{Colors.YELLOW}[CLEANUP SKIPPED]{Colors.RESET} Retaining generated records in Supabase.")
            return

        self.log(f"\n{Colors.BOLD}--- Data Cleanup (Purging Test Records) ---{Colors.RESET}")
        cleanup_plan = [
            ("review", "review_id", self.created_ids["review"]),
            ("boat_booking", "boat_booking_id", self.created_ids["boat_booking"]),
            ("camping_booking", "camp_booking_id", self.created_ids["camping_booking"]),
            ("room_booking", "room_booking_id", self.created_ids["room_booking"]),
            ("shuttle_booking", "shuttle_booking_id", self.created_ids["shuttle_booking"]),
            ("catering", "order_id", self.created_ids["catering"]),
            ("booking", "booking_id", self.created_ids["booking"]),
            ("customer", "customer_id", self.created_ids["customer"]),
        ]

        total_cleaned = 0
        for table, id_col, ids in cleanup_plan:
            if not ids:
                continue
            for record_id in ids:
                try:
                    res = supabase.table(table).delete().eq(id_col, record_id).execute()
                    self.log(f"  {Colors.DIM}[CLEANED]{Colors.RESET} {table:<16} {id_col}={record_id}")
                    total_cleaned += 1
                except Exception as ex:
                    self.log(f"  {Colors.YELLOW}[CLEANUP WARN]{Colors.RESET} {table} {id_col}={record_id} error: {ex}")

        self.log(f"{Colors.GREEN}Successfully purged {total_cleaned} test record(s) from Supabase.{Colors.RESET}")

    def finalize(self) -> bool:
        self.cleanup()

        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        total_time = sum(r.duration_ms for r in self.results)

        self.log(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 75}{Colors.RESET}")
        self.log(f"{Colors.BOLD}TEST SUMMARY{Colors.RESET}")
        self.log(f"{Colors.BOLD}{Colors.HEADER}{'=' * 75}{Colors.RESET}")
        self.log(f"Total Tests Executed : {total}")
        self.log(f"Passed               : {Colors.GREEN}{passed}{Colors.RESET}")
        self.log(f"Failed               : {Colors.RED if failed > 0 else Colors.GREEN}{failed}{Colors.RESET}")
        self.log(f"Total Request Time   : {total_time:.1f}ms")

        if failed > 0:
            self.log(f"\n{Colors.RED}{Colors.BOLD}Failed Tests Breakdown:{Colors.RESET}")
            for r in self.results:
                if not r.passed:
                    self.log(f" - {Colors.RED}{r.name}{Colors.RESET} ({r.endpoint})")
                    self.log(f"   Detail: {r.detail}")
            self.log(f"\n{Colors.RED}Overall Result: FAILED{Colors.RESET}\n")
            return False
        else:
            self.log(f"\n{Colors.GREEN}{Colors.BOLD}Overall Result: ALL TESTS PASSED SUCCESSFULLY!{Colors.RESET}\n")
            return True


# -----------------------------------------------------------------------------
# Pytest test function wrappers so `pytest test_post_methods.py` also works
# -----------------------------------------------------------------------------
def test_all_post_endpoints_in_process():
    client = ApiClientWrapper()
    tester = PostMethodsTester(client=client, verbose=False, fail_fast=False, cleanup=True)
    success = tester.run_all()
    client.close()
    assert success, "One or more API POST tests failed. Review test execution log."


# -----------------------------------------------------------------------------
# Main CLI Entry Point
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Thorough testing script for Enrapture CRM API POST methods."
    )
    parser.add_argument(
        "--url",
        "--base-url",
        dest="base_url",
        type=str,
        default=None,
        help="Optional base URL of a running server (e.g. http://127.0.0.1:8000). If omitted, tests in-process.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print detailed request payloads and server response bodies.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop test execution immediately upon the first failure.",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Keep generated test records in the database rather than deleting them.",
    )

    args = parser.parse_args()

    client = ApiClientWrapper(base_url=args.base_url)
    tester = PostMethodsTester(
        client=client,
        verbose=args.verbose,
        fail_fast=args.fail_fast,
        cleanup=not args.no_cleanup,
    )

    try:
        success = tester.run_all()
    finally:
        client.close()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
