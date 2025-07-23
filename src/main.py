import os
import sys
import subprocess
import json
from typing import Dict, Any
from datetime import datetime, timedelta

from dotenv import load_dotenv
load_dotenv()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda のエントリーポイント"""
    try:
        # 設定ファイル名の必須チェック
        config_file = event.get("config_file_name")
        if not config_file:
            error_msg = "Config file name is required. Please specify 'config_file_name' parameter."
            print(f"ERROR: {error_msg}", flush=True)
            raise Exception(error_msg)
        
        print(f"INFO: Using config file: '{config_file}'", flush=True)
        
        # Embulkのパスは固定（Dockerfileで/embulkに配置）
        embulk_path = "/embulk/bin/embulk"
        config_path_str = f"/embulk/config/{config_file}"
        
        # Embulkコマンドを実行（メモリとパフォーマンス最適化）
        cmd = [
            "java",
            "-Xmx6g",  # 最大ヒープサイズ6GB（8GB環境での安全な設定）
            "-Xms2g",  # 初期ヒープサイズ2GB
            "-XX:+UseG1GC",  # G1ガベージコレクター（大容量メモリに適している）
            "-XX:MaxGCPauseMillis=200",  # GC停止時間を200ms以下に制限
            "-jar", embulk_path,
            "-X", "embulk_home=/embulk",
            "-l", "debug",
            "run", config_path_str
        ]

        print("INFO: Starting Embulk execution...", flush=True)
        
        # リアルタイム出力でタイムアウト設定（13分でLambda制限内）
        try:
            result = subprocess.run(cmd, text=True, timeout=780)
            
            if result.returncode != 0:
                error_msg = f"Embulk execution failed with exit code: {result.returncode}"
                print(f"ERROR: {error_msg}", flush=True)
                raise Exception(error_msg)

            print(f"SUCCESS: Embulk execution completed successfully", flush=True)
            
        except subprocess.TimeoutExpired:
            timeout_msg = "Embulk execution exceeded 13 minutes timeout"
            print(f"ERROR: {timeout_msg}", flush=True)
            raise Exception(timeout_msg)
        
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Embulk execution completed successfully"})
        }
    except Exception as e:
        # エラーログをCloudWatch Logsに記録
        error_msg = str(e)
        print(f"FAILED: {error_msg}", flush=True)
        
        return {
            "statusCode": 500,
            "body": json.dumps({"error": error_msg})
        }


if __name__ == "__main__":
    """ローカルテスト用のメイン実行"""

    # コマンドライン引数でJSON文字列を指定
    if len(sys.argv) > 1:
        event_json = sys.argv[1]
        try:
            event = json.loads(event_json)
        except json.JSONDecodeError as e:
            print(f"エラー: JSON文字列の形式が無効です: {e}")
            sys.exit(1)
    else:
        # 設定ファイル名が必須であることを明示
        print("エラー: コマンドライン引数で設定ファイル名を指定してください。")
        sys.exit(1)
    
    # Lambda関数と同じ処理を実行
    try:
        result = lambda_handler(event, None)
        print(f"結果: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"ローカルテストエラー: {e}")
        sys.exit(1)
    