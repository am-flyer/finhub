import json
import os
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler

from finhub_app.config import get_settings
from finhub_app.feature_store import create_feature_engineering_pipeline
from finhub_app.history import refresh_position_history
from finhub_app.ingestion import create_default_us_ingestion_manager
from finhub_app.orchestration import DataPipelineOrchestrator, build_pipeline_scheduler
from finhub_app.prediction import predict_holdings, predict_symbol, serialize_prediction
from finhub_app.storage import PortfolioStore

pipeline_scheduler: Optional[BackgroundScheduler] = None


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
        elif path == "/api/predictions/holdings":
            self.handle_get_holdings_predictions()
            return
        elif path == "/api/analytics/portfolio":
            self.handle_get_portfolio_analytics()
            return
        elif path == "/api/analytics/stock":
            self.handle_get_stock_analytics()
            return
        elif path == "/api/debug/ingestion-status":
            self.handle_debug_ingestion_status()
            return
        elif path == "/api/debug/feature-sample":
            self.handle_debug_feature_sample()
            return
        elif path == "/api/debug/raw-counts":
            self.handle_debug_raw_counts()
            return
        elif path == "/api/debug/readiness":
            self.handle_debug_readiness()
            return
        elif path == "/api/debug/raw-sample":
            self.handle_debug_raw_sample()
            return
        elif path == "/api/debug/pipeline-jobs":
            self.handle_debug_pipeline_jobs()
            return
        elif path == "/api/debug/scheduler-status":
            self.handle_debug_scheduler_status()
            return
        elif path == "/api/debug/backtest-summary":
            self.handle_debug_backtest_summary()
            return
        elif path == "/api/debug/model-status":
            self.handle_debug_model_status()
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
        elif path == "/api/predictions/estimate":
            self.handle_estimate_prediction()
            return
        elif path == "/api/debug/ingest-symbol":
            self.handle_debug_ingest_symbol()
            return
        elif path == "/api/debug/build-features":
            self.handle_debug_build_features()
            return
        elif path == "/api/debug/sync-symbol":
            self.handle_debug_sync_symbol()
            return
        elif path == "/api/debug/train-model":
            self.handle_debug_train_model()
            return
        elif path == "/api/debug/orchestrate-portfolio":
            self.handle_debug_orchestrate_portfolio()
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
            existing = store.list_positions()
            existing_position = next((p for p in existing if p.symbol == symbol), None)
            if existing_position is None:
                position.added_at = datetime.now()
            else:
                position.added_at = existing_position.added_at or datetime.now()
            store.upsert_position(position)
            refresh_position_history(position, store)
            # Import report generation lazily so the server can start without heavy collectors installed
            try:
                from finhub_app.app import generate_daily_report
                generate_daily_report()
            except Exception:
                # If report generation dependencies are missing, skip automatic report generation
                pass

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

            # Import report generation lazily so the server can start without heavy collectors installed
            try:
                from finhub_app.app import generate_daily_report
                generate_daily_report()
            except Exception:
                pass

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
            # Trigger fresh generation (lazy import so server can run without collectors/pandas)
            try:
                from finhub_app.app import generate_daily_report
                generate_daily_report()
            except Exception:
                # If report generation dependencies are not available, continue without raising
                pass
            
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
            store.initialize()
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
            store.initialize()
            data = store.get_stock_value_history(symbol)
            
            response_data = json.dumps(data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_data)))
            self.end_headers()
            self.wfile.write(response_data)
        except Exception as e:
            self.send_json_error(500, str(e))

    def handle_get_holdings_predictions(self):
        try:
            settings = get_settings()
            store = PortfolioStore(settings.database_url)
            positions = store.list_positions()
            symbols = [p.symbol for p in positions if p.scope == "holding"]
            predictions = [serialize_prediction(pred) for pred in predict_holdings(symbols)]

            response_data = json.dumps(predictions).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_data)))
            self.end_headers()
            self.wfile.write(response_data)
        except Exception as e:
            self.send_json_error(500, str(e))

    def handle_estimate_prediction(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(post_data)

            symbol = (data.get("symbol") or "").strip().upper()
            market = (data.get("market") or "US").strip().upper()
            if not symbol:
                self.send_json_error(400, "Missing required field 'symbol'")
                return

            prediction = serialize_prediction(predict_symbol(symbol, market=market))
            response_data = json.dumps(prediction).encode("utf-8")
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

    def handle_debug_ingestion_status(self):
        try:
            settings = get_settings()
            store = PortfolioStore(settings.database_url)
            store.initialize()
            data = store.get_debug_ingestion_status()
            self.send_json_response(200, data)
        except Exception as e:
            self.send_json_error(500, str(e))

    def handle_debug_feature_sample(self):
        try:
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            symbol = (query_params.get("symbol", [""])[0] or "").strip().upper()
            market = (query_params.get("market", ["US"])[0] or "US").strip().upper()
            as_of_date = (query_params.get("as_of_date", [""])[0] or None)
            limit = int(query_params.get("limit", ["20"])[0] or 20)

            if not symbol:
                self.send_json_error(400, "Missing required query parameter 'symbol'")
                return

            settings = get_settings()
            store = PortfolioStore(settings.database_url)
            store.initialize()
            data = store.get_feature_sample(market, symbol, as_of_date, limit)
            self.send_json_response(200, {"feature_sample": data})
        except ValueError:
            self.send_json_error(400, "Invalid numeric query parameter for limit")
        except Exception as e:
            self.send_json_response(200, {"feature_sample": [], "message": f"Runtime dependency missing or storage not available: {e}"})

    def handle_debug_raw_counts(self):
        try:
            settings = get_settings()
            store = PortfolioStore(settings.database_url)
            store.initialize()
            data = {
                "raw_counts_by_market": store.get_raw_counts_by_market(),
                "ingestion_status": store.get_debug_ingestion_status(),
            }
            self.send_json_response(200, data)
        except Exception as e:
            self.send_json_response(200, {"raw_counts_by_market": {}, "ingestion_status": {}, "message": f"Runtime dependency missing or storage not available: {e}"})

    def handle_debug_backtest_summary(self):
        try:
            data = {
                "status": "not_ready",
                "message": "Backtest summary is not yet available until prediction model training is implemented.",
            }
            self.send_json_response(200, data)
        except Exception as e:
            self.send_json_error(500, str(e))

    def handle_debug_model_status(self):
        try:
            from finhub_app.modeling import get_model_status

            settings = get_settings()
            status = get_model_status(settings)
            self.send_json_response(200, status)
        except Exception as e:
            self.send_json_error(500, str(e))

    def handle_debug_train_model(self):
        try:
            settings = get_settings()
            store = PortfolioStore(settings.database_url)
            store.initialize()
            from finhub_app.modeling import train_model

            metadata = train_model(store, market="US")
            self.send_json_response(200, {
                "success": True,
                "model_version": metadata.model_version,
                "trained_at": metadata.trained_at,
                "sample_count": metadata.sample_count,
                "feature_count": metadata.feature_count,
                "accuracy": metadata.accuracy,
                "roc_auc": metadata.roc_auc,
            })
        except Exception as e:
            self.send_json_error(500, str(e))

    def handle_debug_readiness(self):
        try:
            settings = get_settings()
            store = PortfolioStore(settings.database_url)
            store.initialize()
            data = {
                "readiness": {
                    "raw_status": store.get_debug_raw_status(),
                    "feature_readiness": store.get_debug_feature_readiness(),
                },
                "ingestion_status": store.get_debug_ingestion_status(),
                "raw_counts_by_market": store.get_raw_counts_by_market(),
            }
            self.send_json_response(200, data)
        except Exception as e:
            self.send_json_response(200, {"readiness": {}, "ingestion_status": {}, "raw_counts_by_market": {}, "message": f"Runtime dependency missing or storage not available: {e}"})

    def handle_debug_raw_sample(self):
        try:
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            symbol = (query_params.get("symbol", [""])[0] or "").strip().upper()
            market = (query_params.get("market", ["US"])[0] or "US").strip().upper()
            limit = int(query_params.get("limit", ["20"])[0] or 20)

            if not symbol:
                self.send_json_error(400, "Missing required query parameter 'symbol'")
                return

            settings = get_settings()
            store = PortfolioStore(settings.database_url)
            store.initialize()
            data = store.get_raw_data_sample(market, symbol, limit)
            self.send_json_response(200, {"raw_sample": data})
        except ValueError:
            self.send_json_error(400, "Invalid numeric query parameter for limit")
        except Exception as e:
            self.send_json_error(500, str(e))

    def handle_debug_pipeline_jobs(self):
        try:
            settings = get_settings()
            store = PortfolioStore(settings.database_url)
            store.initialize()
            data = store.list_pipeline_job_statuses()
            self.send_json_response(200, {"pipeline_jobs": data})
        except Exception as e:
            import traceback
            print("DEBUG: exception in handle_debug_pipeline_jobs:")
            traceback.print_exc()
            # Runtime dependencies (storage) may be missing; return a friendly payload so the UI can still load
            self.send_json_response(200, {"pipeline_jobs": [], "message": f"Runtime dependency missing or storage not available: {e}"})

    def handle_debug_scheduler_status(self):
        try:
            global pipeline_scheduler
            if pipeline_scheduler is None:
                self.send_json_response(200, {
                    "scheduler_running": False,
                    "jobs": [],
                    "message": "No background scheduler is currently active.",
                })
                return

            jobs = []
            for job in pipeline_scheduler.get_jobs():
                jobs.append({
                    "id": job.id,
                    "name": getattr(job, "name", None) or job.id,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                    "func_ref": getattr(job.func, "__name__", str(job.func)),
                    "args": job.args,
                    "kwargs": job.kwargs,
                })

            self.send_json_response(200, {
                "scheduler_running": True,
                "jobs": jobs,
            })
        except Exception as e:
            self.send_json_error(500, str(e))

    def handle_debug_orchestrate_portfolio(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(post_data or "{}")
            symbol = (data.get("symbol", "") or "").strip().upper()
            market = (data.get("market", "US") or "US").strip().upper()
            start_date = data.get("start_date")
            end_date = data.get("end_date")

            if not symbol:
                self.send_json_error(400, "Missing required field 'symbol'")
                return
            if market != "US":
                self.send_json_error(400, "Only US ingestion is currently supported")
                return

            start_dt = datetime.fromisoformat(start_date) if start_date else None
            end_dt = datetime.fromisoformat(end_date) if end_date else None

            settings = get_settings()
            store = PortfolioStore(settings.database_url)
            store.initialize()
            ingestion_manager = create_default_us_ingestion_manager(store)
            ingestion_manager.ingest_symbol(symbol, market=market, start_date=start_dt, end_date=end_dt)
            status = store.get_debug_raw_status()
            self.send_json_response(200, {"success": True, "symbol": symbol, "market": market, "raw_status": status})
        except ValueError as e:
            self.send_json_error(400, str(e))
        except Exception as e:
            self.send_json_error(500, str(e))

    def handle_debug_build_features(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(post_data or "{}")
            symbol = (data.get("symbol", "") or "").strip().upper()
            market = (data.get("market", "US") or "US").strip().upper()
            as_of_date = data.get("as_of_date")

            if not symbol:
                self.send_json_error(400, "Missing required field 'symbol'")
                return

            settings = get_settings()
            store = PortfolioStore(settings.database_url)
            store.initialize()
            pipeline = create_feature_engineering_pipeline(store)
            features = pipeline.build_features_for_symbol(symbol, market=market, as_of_date=as_of_date)
            self.send_json_response(200, {"success": True, "symbol": symbol, "market": market, "feature_count": len(features)})
        except ValueError as e:
            self.send_json_error(400, str(e))
        except Exception as e:
            self.send_json_error(500, str(e))

    def handle_debug_sync_symbol(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(post_data or "{}")
            symbol = (data.get("symbol", "") or "").strip().upper()
            market = (data.get("market", "US") or "US").strip().upper()
            start_date = data.get("start_date")
            end_date = data.get("end_date")
            as_of_date = data.get("as_of_date")

            if not symbol:
                self.send_json_error(400, "Missing required field 'symbol'")
                return
            if market != "US":
                self.send_json_error(400, "Only US ingestion is currently supported")
                return

            start_dt = datetime.fromisoformat(start_date) if start_date else None
            end_dt = datetime.fromisoformat(end_date) if end_date else None

            settings = get_settings()
            store = PortfolioStore(settings.database_url)
            store.initialize()
            ingestion_manager = create_default_us_ingestion_manager(store)
            ingestion_manager.ingest_symbol(symbol, market=market, start_date=start_dt, end_date=end_dt)
            pipeline = create_feature_engineering_pipeline(store)
            features = pipeline.build_features_for_symbol(symbol, market=market, as_of_date=as_of_date)
            readiness = {
                "raw_status": store.get_debug_raw_status(),
                "feature_readiness": store.get_debug_feature_readiness(),
            }
            self.send_json_response(200, {
                "success": True,
                "symbol": symbol,
                "market": market,
                "feature_count": len(features),
                "readiness": readiness,
            })
        except ValueError as e:
            self.send_json_error(400, str(e))
        except Exception as e:
            self.send_json_error(500, str(e))

    def send_json_response(self, code, payload):
        response_data = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_data)))
        self.end_headers()
        self.wfile.write(response_data)

    def send_json_error(self, code, message):
        response_data = json.dumps({"error": message}).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_data)))
        self.end_headers()
        self.wfile.write(response_data)



def run_server(port: int = 8000):
    # Attempt lazy initialization of settings and storage. If dependencies are missing,
    # continue running the HTTP server with degraded functionality so the debug UI can still be used.
    settings = None
    store = None
    try:
        settings = get_settings()
        store = PortfolioStore(settings.database_url)
        store.initialize()
    except Exception as e:
        print("WARNING: Could not initialize settings or storage. Some endpoints will return errors:", e)

    server_address = ("", port)
    httpd = ThreadingHTTPServer(server_address, FinhubHTTPRequestHandler)

    global pipeline_scheduler
    pipeline_scheduler = None
    try:
        if store is not None:
            orchestrator = DataPipelineOrchestrator(store)
            pipeline_scheduler = build_pipeline_scheduler(settings, orchestrator)
            pipeline_scheduler.start()
    except Exception as e:
        print("WARNING: Could not start pipeline scheduler (missing optional runtime deps):", e)
        pipeline_scheduler = None

    print(f"\n==========================================")
    print(f"FinHub Pre-Market Dashboard Running")
    print(f"URL: http://localhost:{port}")
    print(f"Scheduler running: {getattr(pipeline_scheduler, 'running', False)}")
    if pipeline_scheduler is not None:
        for job in pipeline_scheduler.get_jobs():
            print(f"Scheduled job: {job.id} next run at {job.next_run_time}")
    print(f"Press Ctrl+C to terminate the server")
    print(f"==========================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        if pipeline_scheduler is not None:
            try:
                pipeline_scheduler.shutdown(wait=False)
            except Exception:
                pass
        httpd.server_close()
