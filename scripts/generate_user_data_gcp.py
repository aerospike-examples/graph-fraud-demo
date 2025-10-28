#!/usr/bin/env python3
"""
Generate user data for fraud detection application with Aerospike Graph CSV format.
Process-pooled + sharded writer: each process writes into the same directory layout,
creating per-worker files named like "<name>-part-<shard>-<num_shards>.csv".

Example use of this generator
python ./scripts/generate_user_data_gcp.py --users 20000 --region american --output ./data/graph_csv --workers 16 --gcs-bucket fraud-demo --gcs-prefix demo/20kUser/ --gcs-delete-local
"""

import argparse
import csv
import os
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed
import random
from faker import Faker
from google.cloud import storage
from google.oauth2 import service_account
from dotenv import load_dotenv, find_dotenv
from multiprocessing import Manager


# ------------------------
# Original configurations (kept identical to preserve semantics)
# ------------------------

fake_us = Faker('en_US')
fake_in = Faker('en_IN')


load_dotenv(find_dotenv(), override=False)
def set_seeds(seed=42):
    """Set random seeds for reproducible data generation"""
    Faker.seed(seed)
    random.seed(seed)

REGIONAL_DATA = {
    'american': {
        'faker': fake_us,
        'cities': [
            "New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia",
            "San Antonio", "San Diego", "Dallas", "San Jose", "Austin", "Jacksonville",
            "Fort Worth", "Columbus", "Charlotte", "San Francisco", "Indianapolis",
            "Seattle", "Denver", "Washington", "Boston", "Nashville", "Detroit",
            "Portland", "Las Vegas", "Memphis", "Louisville", "Baltimore", "Milwaukee",
            "Atlanta", "Kansas City", "Miami", "Colorado Springs", "Raleigh"
        ],
        'banks': [
            "Chase Bank", "Wells Fargo", "Bank of America", "Citibank", "U.S. Bank",
            "PNC Bank", "Capital One", "TD Bank", "BB&T", "SunTrust Bank",
            "Regions Bank", "Fifth Third Bank", "KeyBank", "Huntington Bank"
        ],
        'phone_format': '+1-{area}-{exchange}-{number}',
        'occupations': [
            "Software Engineer", "Marketing Manager", "Financial Analyst", "Sales Representative",
            "Teacher", "Accountant", "Nurse", "Police Officer", "Graphic Designer",
            "Project Manager", "Data Scientist", "Construction Manager", "HR Specialist",
            "Web Developer", "Real Estate Agent", "Doctor", "Lawyer", "Chef", "Electrician",
            "Plumber", "Mechanic", "Dentist", "Architect", "Engineer", "Consultant"
        ]
    },
    'indian': {
        'faker': fake_in,
        'cities': [
            "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Ahmedabad", "Chennai", "Kolkata",
            "Pune", "Jaipur", "Lucknow", "Kanpur", "Nagpur", "Indore", "Thane", "Bhopal",
            "Visakhapatnam", "Pimpri-Chinchwad", "Patna", "Vadodara", "Ghaziabad", "Ludhiana",
            "Agra", "Nashik", "Faridabad", "Meerut", "Rajkot", "Kalyan-Dombivli", "Vasai-Virar",
            "Varanasi", "Srinagar", "Dhanbad", "Jodhpur", "Amritsar", "Raipur", "Allahabad"
        ],
        'banks': [
            "State Bank of India", "HDFC Bank", "ICICI Bank", "Punjab National Bank",
            "Canara Bank", "Union Bank of India", "Axis Bank", "Bank of Baroda",
            "Indian Overseas Bank", "Central Bank of India", "Indian Bank", "Yes Bank",
            "Kotak Mahindra Bank", "Federal Bank", "IDBI Bank", "Syndicate Bank"
        ],
        'phone_format': '+91-{area}-{number}',
        'occupations': [
            "Software Engineer", "Teacher", "Accountant", "Sales Representative",
            "Marketing Manager", "Nurse", "Police Officer", "Data Scientist",
            "HR Specialist", "Web Developer", "Graphic Designer", "Financial Analyst",
            "Project Manager", "Real Estate Agent", "Construction Manager", "Doctor",
            "Government Officer", "Bank Manager", "Shopkeeper", "Farmer", "Driver",
            "Engineer", "Consultant", "Business Owner", "Professor"
        ]
    }
}

DEVICE_TYPES = ["mobile", "desktop", "tablet"]
OPERATING_SYSTEMS = {
    "mobile": ["Android 13", "Android 12", "iOS 16", "iOS 15", "Android 11"],
    "desktop": ["Windows 11", "Windows 10", "macOS Ventura", "macOS Monterey", "Ubuntu 22.04"],
    "tablet": ["iPadOS 16", "Android 12", "iPadOS 15", "Android 11"]
}
BROWSERS = {
    "mobile": ["Chrome Mobile", "Safari Mobile", "Firefox Mobile", "Samsung Internet"],
    "desktop": ["Chrome", "Firefox", "Safari", "Edge", "Opera"],
    "tablet": ["Safari", "Chrome", "Firefox"]
}
ACCOUNT_TYPES = ["savings", "checking", "credit"]

# ------------------------
# Buffered CSV Writer (per process)
# ------------------------

class CsvBufferedWriter:
    def __init__(self, path, header, flush_every=2000):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.f = open(self.path, 'w', newline='', encoding='utf-8')
        self.writer = csv.writer(self.f)
        self.writer.writerow(header)
        self.buf = []
        self.flush_every = flush_every

    def write_row(self, row):
        self.buf.append(row)
        if len(self.buf) >= self.flush_every:
            self.writer.writerows(self.buf)
            self.buf.clear()

    def close(self):
        if self.buf:
            self.writer.writerows(self.buf)
            self.buf.clear()
        self.f.flush()
        self.f.close()

def _ensure_prefix(prefix: str) -> str:
    if not prefix:
        return ""
    return prefix if prefix.endswith("/") else prefix + "/"

def gcs_upload_file(local_path: Path, bucket_name: str, object_name: str, bucket):
    if storage is None:
        raise RuntimeError("google-cloud-storage not installed. Run: pip install google-cloud-storage")

    blob = bucket.blob(object_name)
    blob.upload_from_filename(str(local_path))

# ------------------------
# Per-shard generator
# ------------------------

def run_shard(shard_id:int, start_user_index:int, num_users:int, total_users:int,
              region:str, output_dir:str, seed:int, num_shards:int,
              gcs_bucket: str | None, gcs_prefix: str, gcs_delete_local: bool, shared):
    """
    shard_id: 0..num_shards-1
    start_user_index: global 0-based index of first user handled by this shard
    num_users: users to generate in this shard
    total_users: total across all shards (for ID formatting / ratios)
    """
    # Locale-specific faker; one instance per process
    locale = 'en_US' if region == 'american' else 'en_IN'
    faker = Faker(locale)
    # Seed per-shard deterministically
    shard_seed = (seed * 73856093) ^ shard_id
    Faker.seed(shard_seed)
    rnd = random.Random(shard_seed)

    # Top-level directories (same as original)
    out_root = Path(output_dir)
    (out_root / "vertices" / "users").mkdir(parents=True, exist_ok=True)
    (out_root / "vertices" / "accounts").mkdir(parents=True, exist_ok=True)
    (out_root / "vertices" / "devices").mkdir(parents=True, exist_ok=True)
    (out_root / "edges" / "ownership").mkdir(parents=True, exist_ok=True)
    (out_root / "edges" / "usage").mkdir(parents=True, exist_ok=True)

    # File names with part suffix
    part_tag = f"part-{shard_id+1}-{num_shards}"
    users_w = CsvBufferedWriter(out_root / "vertices" / "users" / f"users-{part_tag}.csv",
                                ['~id', '~label', 'name:String', 'email:String', 'phone:String',
                                 'age:Int', 'location:String', 'occupation:String', 'risk_score:Double', 'signup_date:Date'])
    accounts_w = CsvBufferedWriter(out_root / "vertices" / "accounts" / f"accounts-{part_tag}.csv",
                                   ['~id', '~label', 'type:String', 'balance:Double', 'bank_name:String',
                                    'status:String', 'created_date:Date', 'fraud_flag:Boolean'])
    devices_w = CsvBufferedWriter(out_root / "vertices" / "devices" / f"devices-{part_tag}.csv",
                                  ['~id', '~label', 'type:String', 'os:String', 'browser:String', 'fingerprint:String',
                                   'first_seen:Date', 'last_login:Date', 'login_count:Int', 'fraud_flag:Boolean'])
    owns_w = CsvBufferedWriter(out_root / "edges" / "ownership" / f"owns-{part_tag}.csv",
                               ['~from', '~to', '~label', 'since:Date'])
    uses_w = CsvBufferedWriter(out_root / "edges" / "usage" / f"uses-{part_tag}.csv",
                               ['~from', '~to', '~label', 'first_used:Date', 'last_used:Date', 'usage_count:Int'])

    # ---- Device ID range reserved for this shard to ensure global uniqueness
    block_size = 9_000_000 // max(1, num_shards)
    device_base = shard_id * block_size  # local counter adds to this
    device_counter = 0
    def new_device_id():
        nonlocal device_counter
        device_counter += 1
        val = device_base + device_counter
        return f"DEV{val:07d}"  # safely extends beyond if needed (string grows)

    def next_account_id():
        with shared['lock']:
            shared['counter'].value += 1
            return f"A{shared['counter'].value:09d}"
    # ---- Build device pool & shared groups within this shard
    base_devices = int(num_users * 3.5)
    min_devices = num_users + 500
    max_reasonable_devices = min(10_000_000, base_devices)
    max_devices = max(min_devices, max_reasonable_devices)

    device_pool = []
    estimated_shared_devices = min(1000, num_users // 10)
    now = datetime.utcnow()
    for _ in range(estimated_shared_devices):
        device_type = rnd.choice(DEVICE_TYPES)
        dev = {
            'id': new_device_id(),
            'type': device_type,
            'os': rnd.choice(OPERATING_SYSTEMS[device_type]),
            'browser': rnd.choice(BROWSERS[device_type]),
            'fingerprint': faker.sha256(),
            'first_seen': (now - timedelta(days=rnd.randint(0, 500))).strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        device_pool.append(dev)

    num_groups = min(100, max(3, num_users // 50))
    shared_device_groups = []
    for i in range(num_groups):
        if i == 0:
            group_size = rnd.randint(3, 4); num_shared = 2
        elif i == 1:
            group_size = 2; num_shared = 3
        else:
            group_size = rnd.randint(2, 3); num_shared = rnd.randint(1, 2)
        if num_users >= group_size and len(device_pool) >= num_shared:
            user_indices = rnd.sample(range(num_users), group_size)
            shared_devices = rnd.sample(device_pool, num_shared)
            shared_device_groups.append({'users': set(user_indices), 'devices': shared_devices})

    written_device_ids = set()

    def generate_user(user_idx:int):
        user_id = f"U{(user_idx + 1):07d}"
        name = faker.name()
        if region == 'american':
            phone = f"+1-{rnd.randint(200, 999)}-{rnd.randint(200, 999)}-{rnd.randint(1000, 9999)}"
        else:
            phone = f"+91-{rnd.randint(70000, 99999)}-{rnd.randint(10000, 99999)}"
        email = f"{name.lower().replace(' ', '.')}@{faker.domain_name()}"
        age = rnd.randint(18, 70)
        location = rnd.choice(REGIONAL_DATA[region]['cities'])
        occupation = rnd.choice(REGIONAL_DATA[region]['occupations'])
        risk_score = round(rnd.uniform(0, 100), 1)
        signup_date = (now - timedelta(days=rnd.randint(0, 730))).strftime('%Y-%m-%dT%H:%M:%SZ')
        return {
            'id': user_id, 'name': name, 'email': email, 'phone': phone, 'age': age,
            'location': location, 'occupation': occupation, 'risk_score': risk_score, 'signup_date': signup_date
        }

    def allocate_devices(count:int):
        nonlocal device_counter
        available = max(0, max_devices - device_counter)
        if count > available:
            count = available
        out = []
        for _ in range(count):
            device_type = rnd.choice(DEVICE_TYPES)
            dev = {
                'id': new_device_id(),
                'type': device_type,
                'os': rnd.choice(OPERATING_SYSTEMS[device_type]),
                'browser': rnd.choice(BROWSERS[device_type]),
                'fingerprint': faker.sha256(),
                'first_seen': (now - timedelta(days=rnd.randint(0, 500))).strftime('%Y-%m-%dT%H:%M:%SZ')
            }
            out.append(dev)
        return out

    # Main loop for this shard
    for local_i in range(num_users):
        global_i = start_user_index + local_i
        user = generate_user(global_i)

        # Accounts
        num_accounts = rnd.choices([1, 2, 3, 4], weights=[0.3, 0.4, 0.2, 0.1])[0]
        accounts = []
        for j in range(num_accounts):
            account_id = next_account_id()
            account_type = rnd.choice(ACCOUNT_TYPES)
            if account_type == "credit":
                balance = round(rnd.uniform(-50000, 0), 2)
            elif account_type == "savings":
                balance = round(rnd.uniform(1000, 500000), 2)
            else:
                balance = round(rnd.uniform(100, 50000), 2)
            bank_name = rnd.choice(REGIONAL_DATA[region]['banks'])
            created_date = (now - timedelta(days=rnd.randint(0, 1000))).strftime('%Y-%m-%dT%H:%M:%SZ')
            fraud_flag = rnd.random() < 0.1

            accounts.append({
                'id': account_id, 'type': account_type, 'balance': balance,
                'bank_name': bank_name, 'status': 'active',
                'created_date': created_date, 'fraud_flag': fraud_flag
            })

        # Devices
        user_devices = []
        in_group = None
        for g in shared_device_groups:
            if local_i in g['users']:
                in_group = g
                break
        if in_group:
            user_devices.extend(in_group['devices'])
            if rnd.random() < 0.4:
                user_devices.extend(allocate_devices(rnd.randint(1, 2)))
        else:
            desired = rnd.choices([1, 2, 3, 4, 5], weights=[0.15, 0.35, 0.30, 0.15, 0.05])[0]
            user_devices = allocate_devices(desired)

        # Enrich
        enriched = []
        for d in user_devices:
            last_login = (now - timedelta(days=rnd.randint(0, 30), hours=rnd.randint(0, 23))).strftime('%Y-%m-%dT%H:%M:%SZ')
            login_count = rnd.randint(5, 200)
            dev = dict(d)
            dev['last_login'] = last_login
            dev['login_count'] = login_count
            dev['fraud_flag'] = rnd.random() < 0.05
            enriched.append(dev)

        # Writes
        users_w.write_row([
            user['id'], 'user', user['name'], user['email'], user['phone'],
            user['age'], user['location'], user['occupation'], user['risk_score'], user['signup_date']
        ])
        for acc in accounts:
            accounts_w.write_row([
                acc['id'], 'account', acc['type'], acc['balance'], acc['bank_name'],
                acc['status'], acc['created_date'], acc['fraud_flag']
            ])
            owns_w.write_row([user['id'], acc['id'], 'OWNS', acc['created_date']])
        for d in enriched:
            if d['id'] not in written_device_ids:
                written_device_ids.add(d['id'])
                devices_w.write_row([
                    d['id'], 'device', d['type'], d['os'], d['browser'], d['fingerprint'],
                    d['first_seen'], d['last_login'], d['login_count'], d['fraud_flag']
                ])
            uses_w.write_row([user['id'], d['id'], 'USES', d['first_seen'], d['last_login'], d['login_count']])

        if (local_i + 1) % 5000 == 0:
            print(f"[{part_tag}] {local_i+1}/{num_users} users")

    users_w.close(); accounts_w.close(); devices_w.close(); owns_w.close(); uses_w.close()
    if gcs_bucket:
        # Map local files to GCS object keys (preserve directory layout under provided prefix)
        paths = [
            ("vertices/users", users_w.path.name),
            ("vertices/accounts", accounts_w.path.name),
            ("vertices/devices", devices_w.path.name),
            ("edges/ownership", owns_w.path.name),
            ("edges/usage", uses_w.path.name),
        ]
        credentials = service_account.Credentials.from_service_account_file(
            "C:/Repos/.features/gcp/firefly-aerospike-2466551ab7a3.json"
        )
        client = storage.Client(credentials=credentials, project=os.getenv('GCP_PROJECT'))
        bucket = client.bucket(os.getenv('GCP_BUCKET_NAME'))
        for subdir, fname in paths:
            local = (Path(output_dir) / subdir / fname).resolve()
            object_name = f"{gcs_prefix}{subdir}/{fname}"
            gcs_upload_file(local, gcs_bucket, object_name, bucket)
            if gcs_delete_local:
                try:
                    local.unlink()
                except Exception:
                    pass
    return f"{part_tag}: users={num_users}, devices_written={len(written_device_ids)}"

# ------------------------
# Orchestrator
# ------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate user data (Aerospike Graph CSV) - process pooled & sharded (flat file naming)")
    parser.add_argument("--users", type=int, default=100, help="Total number of users to generate (default: 100)")
    parser.add_argument("--region", choices=['indian', 'american'], default='american', help="Demographics region (default: american)")
    parser.add_argument("--output", default="./data/graph_csv", help="Output directory (default: ./data/graph_csv)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument("--workers", type=int, default=None, help="Process pool size (default: CPU count)")
    parser.add_argument("--gcs-bucket", default=None, help="If set, upload outputs to this GCS bucket")
    parser.add_argument("--gcs-prefix", default="", help="Optional object key prefix in the bucket (e.g. myrun/2025-10-22/)")
    parser.add_argument("--gcs-delete-local", action="store_true", help="Delete local files after successful upload")
    args = parser.parse_args()

    set_seeds(args.seed)
    total_users = args.users
    workers = args.workers or (os.cpu_count() or 4)
    workers = max(1, workers)

    # Split users into near-equal shards
    per = total_users // workers
    rem = total_users % workers
    plan = []
    start = 0
    for sid in range(workers):
        count = per + (1 if sid < rem else 0)
        if count == 0:
            continue
        plan.append((sid, start, count))
        start += count

    print(f"Generating {total_users:,} {args.region} users across {len(plan)} partitions -> {args.output}")

    import time
    t0 = time.time()
    results = []
    with Manager() as manager:
        shared = {
            'counter': manager.Value('q', 0),
            'lock': manager.Lock(),
        }
        with ProcessPoolExecutor(max_workers=len(plan)) as ex:
            futs = []
            for sid, sidx, cnt in plan:
                fut = fut = ex.submit(
                    run_shard,
                    sid, sidx, cnt, total_users,
                    args.region, args.output, args.seed, len(plan),
                    args.gcs_bucket, _ensure_prefix(args.gcs_prefix), args.gcs_delete_local, shared
                )
                futs.append(fut)
            for f in as_completed(futs):
                results.append(f.result())
    dt = time.time() - t0

    for r in sorted(results):
        print("✔", r)
    rate = total_users / dt if dt > 0 else 0.0
    print(f"\n✅ Done. {total_users:,} users in {dt:.2f}s  (~{rate:.0f} users/sec)")
    print(f"Files are in:")
    print(f"  {args.output}/vertices/users/users-part-*-{len(plan)}.csv")
    print(f"  {args.output}/vertices/accounts/accounts-part-*-{len(plan)}.csv")
    print(f"  {args.output}/vertices/devices/devices-part-*-{len(plan)}.csv")
    print(f"  {args.output}/edges/ownership/owns-part-*-{len(plan)}.csv")
    print(f"  {args.output}/edges/usage/uses-part-*-{len(plan)}.csv")

if __name__ == "__main__":
    main()
