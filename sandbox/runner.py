import subprocess
import time
import json

IMAGE = "code-runner-python"
TIMEOUT = 2
MAX_OUTPUT = 64 * 1024  # 64 KB

code = "a = int(input()); print(a * 2)"

test_cases = [
    {"input": "1\n", "expected": "2"},
    {"input": "5\n", "expected": "10"},
    {"input": "21\n", "expected": "42"},
]

def run_test(input_data: str):
    cmd = [
        "docker", "run", "--rm", "-i",
        "--network=none",
        "--read-only",
        "--memory=256m",
        "--cpus=0.5",
        IMAGE,
        "python3", "-c", code
    ]

    start = time.time()

    try:
        result = subprocess.run(
            cmd,
            input=input_data.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=TIMEOUT
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "time": round(time.time() - start, 3)
        }

    stdout = result.stdout[:MAX_OUTPUT].decode(errors="ignore").strip()
    stderr = result.stderr[:MAX_OUTPUT].decode(errors="ignore").strip()
    elapsed = round(time.time() - start, 3)

    if result.returncode != 0:
        return {
            "status": "runtime_error",
            "stderr": stderr,
            "time": elapsed
        }

    return {
        "status": "ok",
        "stdout": stdout,
        "time": elapsed
    }


results = []
overall_status = "accepted"
total_time = 0.0

for idx, tc in enumerate(test_cases, start=1):
    res = run_test(tc["input"])
    total_time += res.get("time", 0)

    test_result = {
        "index": idx,
        "input": tc["input"].strip(),
        "expected": tc["expected"],
        "time": res.get("time"),
        "status": res["status"]
    }

    if res["status"] == "ok":
        test_result["output"] = res["stdout"]
        if res["stdout"] != tc["expected"]:
            test_result["status"] = "wrong_answer"
            overall_status = "wrong_answer"
            results.append(test_result)
            break
    else:
        overall_status = res["status"]
        if "stderr" in res:
            test_result["stderr"] = res["stderr"]
        results.append(test_result)
        break

    results.append(test_result)

final_result = {
    "status": overall_status,
    "total_time": round(total_time, 3),
    "tests": results
}

print(json.dumps(final_result, indent=2))
