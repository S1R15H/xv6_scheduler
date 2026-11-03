#!/usr/bin/env python3
"""Ask a local Ollama model for one validated xv6 ticket recommendation."""

import argparse
import csv
import json
import socket
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MIN_TICKETS = 10
MAX_TICKETS = 200
TICKET_STEP = 10


def read_monitor_csv(path, selected_pids):
    samples = {pid: [] for pid in selected_pids}
    try:
        with open(path, newline="", encoding="utf-8") as monitor_file:
            reader = csv.DictReader(monitor_file)
            required = {"time", "pid", "tickets", "ticks"}
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                raise ValueError("CSV must have time,pid,tickets,ticks columns")

            for line_number, row in enumerate(reader, start=2):
                try:
                    pid = int(row["pid"])
                except (TypeError, ValueError):
                    raise ValueError("line {} has an invalid pid".format(line_number))
                if pid not in samples:
                    continue
                try:
                    sample = {
                        "time": int(row["time"]),
                        "tickets": int(row["tickets"]),
                        "ticks": int(row["ticks"]),
                    }
                except (TypeError, ValueError):
                    raise ValueError("line {} has invalid numeric data".format(line_number))
                if sample["tickets"] < MIN_TICKETS or sample["tickets"] > MAX_TICKETS:
                    raise ValueError("line {} has tickets outside 10..200".format(line_number))
                if sample["tickets"] % TICKET_STEP:
                    raise ValueError("line {} has tickets not divisible by 10".format(line_number))
                if sample["ticks"] < 0:
                    raise ValueError("line {} has a negative tick count".format(line_number))
                samples[pid].append(sample)
    except (OSError, UnicodeError, csv.Error) as error:
        raise ValueError("cannot read {}: {}".format(path, error))

    summaries = []
    for pid, observations in samples.items():
        if len(observations) < 2:
            raise ValueError("PID {} needs at least two monitor samples".format(pid))
        observations.sort(key=lambda sample: sample["time"])
        if any(a["ticks"] > b["ticks"] for a, b in zip(observations, observations[1:])):
            raise ValueError("PID {} tick counts went backwards".format(pid))
        delta = observations[-1]["ticks"] - observations[0]["ticks"]
        summaries.append({
            "pid": pid,
            "tickets": observations[-1]["tickets"],
            "delta_ticks": delta,
            "samples": len(observations),
        })

    total_ticks = sum(item["delta_ticks"] for item in summaries)
    if total_ticks <= 0:
        raise ValueError("selected processes received no ticks in the sample window")
    for item in summaries:
        item["observed_share_percent"] = round(100.0 * item["delta_ticks"] / total_ticks, 1)
    return summaries


def validate_recommendation(response_text, target_pid):
    try:
        recommendation = json.loads(response_text)
    except (TypeError, ValueError) as error:
        raise ValueError("Ollama response was not valid JSON: {}".format(error))
    if not isinstance(recommendation, dict):
        raise ValueError("Ollama response must be a JSON object")
    if set(recommendation) != {"pid", "new_tickets", "reason"}:
        raise ValueError("response must contain exactly pid, new_tickets, and reason")

    pid = recommendation["pid"]
    tickets = recommendation["new_tickets"]
    reason = recommendation["reason"]
    if isinstance(pid, bool) or not isinstance(pid, int) or pid != target_pid:
        raise ValueError("recommendation PID must be the requested target PID")
    if isinstance(tickets, bool) or not isinstance(tickets, int):
        raise ValueError("new_tickets must be an integer")
    if tickets < MIN_TICKETS or tickets > MAX_TICKETS or tickets % TICKET_STEP:
        raise ValueError("new_tickets must be 10..200 in multiples of 10")
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 300:
        raise ValueError("reason must be a non-empty string of at most 300 characters")
    return {"pid": pid, "new_tickets": tickets, "reason": reason.strip()}


def ask_ollama(url, model, prompt, timeout):
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }).encode("utf-8")
    request = Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise ValueError("Ollama returned HTTP {}: {}".format(error.code, error.reason))
    except URLError as error:
        raise ValueError("cannot reach Ollama at {}: {}".format(url, error.reason))
    except (socket.timeout, TimeoutError):
        raise ValueError("Ollama request timed out after {} seconds".format(timeout))
    except (UnicodeDecodeError, ValueError) as error:
        raise ValueError("invalid response from Ollama: {}".format(error))
    if not isinstance(result, dict) or not isinstance(result.get("response"), str):
        raise ValueError("Ollama response is missing its generated text")
    return result["response"]


def make_prompt(summaries, target_pid, target_share):
    data = json.dumps(summaries, separators=(",", ":"))
    return (
        "You advise on an xv6 STRIDE scheduler. Recommend a ticket count for exactly "
        "the target process to move its measured CPU share toward the requested share. "
        "Do not change any other process. Tickets must be an integer from 10 to 200 "
        "inclusive, in multiples of 10. The observation data is: " + data +
        "\nTarget PID: " + str(target_pid) +
        "\nTarget share goal: " + str(target_share) +
        "% of the selected workload's CPU ticks." +
        '\nReturn only a JSON object with exactly these fields: '
        '{"pid": integer, "new_tickets": integer, "reason": string}.'
    )


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Get one bounded ticket recommendation from a local Ollama model."
    )
    parser.add_argument("csv_file", help="monitor output CSV (time,pid,tickets,ticks)")
    parser.add_argument("--target-pid", required=True, type=int,
                        help="only PID the model is allowed to recommend changing")
    parser.add_argument("--target-share", required=True, type=float,
                        help="desired CPU share for the target, from 1 to 99 percent")
    parser.add_argument("--peer-pid", required=True, type=int, action="append",
                        help="another workload PID to include; repeat for more peers")
    parser.add_argument("--model", default="llama3.1", help="local Ollama model name")
    parser.add_argument("--ollama-url", default="http://localhost:11434/api/generate",
                        help="Ollama generate API URL")
    parser.add_argument("--timeout", type=int, default=120, help="Ollama timeout in seconds")
    args = parser.parse_args(argv)
    if not 1 <= args.target_share <= 99:
        parser.error("--target-share must be between 1 and 99")
    if args.target_pid in args.peer_pid or len(set(args.peer_pid)) != len(args.peer_pid):
        parser.error("target and peer PIDs must be distinct")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    return args


def main(argv=None):
    args = parse_args(argv)
    try:
        pids = [args.target_pid] + args.peer_pid
        summaries = read_monitor_csv(args.csv_file, pids)
        prompt = make_prompt(summaries, args.target_pid, args.target_share)
        generated = ask_ollama(args.ollama_url, args.model, prompt, args.timeout)
        recommendation = validate_recommendation(generated, args.target_pid)
        print(json.dumps(recommendation))
    except ValueError as error:
        print("scheduler_advisor: {}".format(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
