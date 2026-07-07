import json
import os
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from finhub_app.app import generate_daily_report
from finhub_app.config import get_settings
from finhub_app.storage import PortfolioStore


class FinhubHTTPRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence standard HTTP logs to keep terminal output clean
        pass

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # REST API Routes
        if path == "/api/reports":
            self.handle_list_reports()
            return
        elif path.startswith("/api/reports/"):
            self.handle_get_report(path)
            return
        elif path == "/api/positions":
            self.handle_list_positions()
            return
        elif path == "/api/analytics/portfolio":
            self.handle_get_portfolio_analytics()
            return
        elif path == "/api/analytics/stock":
            self.handle_get_stock_analytics()
            return
        elif path == "/api/news":
            self.handle_get_news()
            return

        # Static Files Routing
        self.handle_static_file(path)

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == "/api/reports/generate":
            self.handle_generate_report()
            return
        elif path == "/api/positions":
            self.handle_upsert_position()
            return

        self.send_error(404, "Endpoint not found")

    def do_DELETE(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path.startswith("/api/positions/"):
            self.handle_delete_position(path)
            return
        elif path.startswith("/api/reports/"):
            self.handle_delete_report(path)
            return

        self.send_error(404, "Endpoint not found")

    def handle_static_file(self, path):
        # Clean path and default to index.html
        if path == "/":
            path = "/index.html"

        # Safe directory joining
        web_dir = Path(__file__).parent.parent / "frontend" / "dist"
        file_path = (web_dir / path.lstrip("/")).resolve()

        # Prevent Directory Traversal Vulnerability
        if not str(file_path).startswith(str(web_dir.resolve())):
            self.send_error(403, "Access Denied")
            return

        if not file_path.exists() or file_path.is_dir():
            self.send_error(404, "File Not Found")
            return

        # Determine Content Type
        content_type = "text/plain"
        if file_path.suffix == ".html":
            content_type = "text/html"
        elif file_path.suffix == ".css":
            content_type = "text/css"
        elif file_path.suffix == ".js":
            content_type = "application/javascript"

        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {e}")

    def handle_upsert_position(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(post_data)

            symbol = data.get("symbol", "").upper().strip()
            name = data.get("name", "").strip() or None
            quantity = float(data.get("quantity", 0))
            
            average_cost = data.get("average_cost")
            if average_cost is not None and str(average_cost).strip() != "":
                average_cost = float(average_cost)
            else:
                average_cost = None

            scope_val = data.get("scope", "holding").strip()

            from finhub_app.domain import Position, AssetScope
            position = Position(
                symbol=symbol,
                name=name,
                quantity=quantity,
                average_cost=average_cost,
                scope=AssetScope(scope_val),
            )

            settings = get_settings()
            store = PortfolioStore(settings.database_url)
            store.initialize()
            store.upsert_position(position)

            response_data = json.dumps({"success": True, "symbol": symbol}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_data)))
            self.end_headers()
            self.wfile.write(response_data)
        except Exception as e:
            self.send_json_error(400, str(e))

    def handle_delete_position(self, path):
        try:
            parts = path.split("/")
            symbol = parts[-1].upper().strip()

            settings = get_settings()
            store = PortfolioStore(settings.database_url)
            store.initialize()
            success = store.delete_position(symbol)

            if not success:
                self.send_json_error(404, f"Position for {symbol} not found")
                return

            response_data = json.dumps({"success": True, "symbol": symbol}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_data)))
            self.end_headers()
            self.wfile.write(response_data)
        except Exception as e:
            self.send_json_error(500, str(e))

    def handle_delete_report(self, path):
        try:
            parts = path.split("/")
            report_id = int(parts[-1])

            settings = get_settings()
            store = PortfolioStore(settings.database_url)
            success = store.delete_report(report_id)

            if not success:
                self.send_json_error(404, f"Report with ID {report_id} not found")
                return

            response_data = json.dumps({"success": True, "id": report_id}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_data)))
            self.end_headers()
            self.wfile.write(response_data)
        except Exception as e:
            self.send_json_error(500, str(e))

    def handle_list_reports(self):
        try:
            settings = get_settings()
            store = PortfolioStore(settings.database_url)
            reports = store.list_reports()
            
            response_data = json.dumps(reports).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_data)))
            self.end_headers()
            self.wfile.write(response_data)
        except Exception as e:
            self.send_json_error(500, str(e))

    def handle_get_report(self, path):
        try:
            # Extract ID from path
            parts = path.split("/")
            report_id = int(parts[-1])
            
            settings = get_settings()
            store = PortfolioStore(settings.database_url)
            report = store.get_report(report_id)
            
            if not report:
                self.send_error(404, "Report Not Found")
                return
                
            response_data = json.dumps(report).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_data)))
            self.end_headers()
            self.wfile.write(response_data)
        except ValueError:
            self.send_error(400, "Invalid Report ID format")
        except Exception as e:
            self.send_json_error(500, str(e))

    def handle_list_positions(self):
        try:
            settings = get_settings()
            store = PortfolioStore(settings.database_url)
            positions = store.list_positions()
            
            positions_data = [
                {
                    "symbol": p.symbol,
                    "name": p.name,
                    "quantity": p.quantity,
                    "average_cost": p.average_cost,
                    "scope": p.scope.value,
                }
                for p in positions
            ]
            response_data = json.dumps(positions_data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_data)))
            self.end_headers()
            self.wfile.write(response_data)
        except Exception as e:
            self.send_json_error(500, str(e))

    def handle_generate_report(self):
        try:
            # Trigger fresh generation
            generate_daily_report()
            
            # Fetch latest
            settings = get_settings()
            store = PortfolioStore(settings.database_url)
            reports = store.list_reports()
            
            if not reports:
                self.send_json_error(500, "Report generated but could not be found.")
                return
                
            latest_report_meta = reports[0]
            latest_report = store.get_report(latest_report_meta["id"])
            
            response_data = json.dumps(latest_report).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_data)))
            self.end_headers()
            self.wfile.write(response_data)
        except Exception as e:
            import traceback
            print("ERROR: Report generation failed:")
            traceback.print_exc()
            self.send_json_error(500, str(e))

    def handle_get_portfolio_analytics(self):
        try:
            settings = get_settings()
            store = PortfolioStore(settings.database_url)
            data = store.get_portfolio_value_history()
            
            response_data = json.dumps(data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_data)))
            self.end_headers()
            self.wfile.write(response_data)
        except Exception as e:
            self.send_json_error(500, str(e))

    def handle_get_stock_analytics(self):
        try:
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            symbols = query_params.get("symbol", [])
            if not symbols:
                self.send_json_error(400, "Missing required parameter 'symbol'")
                return
                
            symbol = symbols[0].upper().strip()
            settings = get_settings()
            store = PortfolioStore(settings.database_url)
            data = store.get_stock_value_history(symbol)
            
            response_data = json.dumps(data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_data)))
            self.end_headers()
            self.wfile.write(response_data)
        except Exception as e:
            self.send_json_error(500, str(e))

    def handle_get_news(self):
        try:
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            symbols = query_params.get("symbol", [])
            symbol = symbols[0].upper().strip() if symbols else "PORTFOLIO"
            limits = query_params.get("limit", ["10"])
            offsets = query_params.get("offset", ["0"])
            dates = query_params.get("date", [])
            
            limit = int(limits[0])
            offset = int(offsets[0])
            date_val = dates[0].strip() if dates else None
            
            settings = get_settings()
            store = PortfolioStore(settings.database_url)
            
            # Skip fresh yfinance fetch if filtering by a specific historical date or PORTFOLIO
            if offset == 0 and not date_val and symbol != "PORTFOLIO":
                try:
                    import yfinance as yf
                    import html
                    from finhub_app.seeding import calculate_simple_sentiment
                    ticker = yf.Ticker(symbol)
                    news_items = ticker.news
                    for item in news_items:
                        title = item.get("title", "")
                        summary = item.get("summary", "")
                        source = item.get("publisher", "Yahoo Finance")
                        url = item.get("link", "")
                        pub_time = item.get("providerPublishTime", 0)

                        title = html.unescape(title).replace("\xa0", " ").strip()
                        summary = html.unescape(summary).replace("\xa0", " ").strip() if summary else ""
 
                        published_at = datetime.fromtimestamp(pub_time) if pub_time else datetime.now()
                        sentiment = calculate_simple_sentiment(title + " " + (summary or ""))
                        
                        store.save_news_record(
                            symbol=symbol,
                            published_at=published_at,
                            title=title,
                            summary=summary,
                            source=source,
                            url=url,
                            sentiment_score=sentiment
                        )
                except Exception as ex:
                    print(f"Warning: Failed to fetch fresh news for {symbol}: {ex}")
            
            data = store.get_paginated_news(symbol, limit, offset, date_val)
            
            response_data = json.dumps(data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_data)))
            self.end_headers()
            self.wfile.write(response_data)
        except Exception as e:
            self.send_json_error(500, str(e))

    def send_json_error(self, code, message):
        response_data = json.dumps({"error": message}).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_data)))
        self.end_headers()
        self.wfile.write(response_data)



def run_server(port: int = 8000):
    server_address = ("", port)
    httpd = ThreadingHTTPServer(server_address, FinhubHTTPRequestHandler)
    print(f"\n==========================================")
    print(f"FinHub Pre-Market Dashboard Running")
    print(f"URL: http://localhost:{port}")
    print(f"Press Ctrl+C to terminate the server")
    print(f"==========================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()
