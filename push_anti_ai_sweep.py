import subprocess

cwd = r"C:\Users\Nguyen Trong Khoi\Downloads\CLOUD"

msg = "feat(anti-ai-sweep): comprehensive purge of AI clichés, conversational artifacts, raw emojis, and em-dashes across codebase, UI, and docs"

# Stage all files
r_add = subprocess.run(["git", "add", "-A"], capture_output=True, text=True, cwd=cwd)
print("GIT ADD:", r_add.returncode)

# Commit
r_commit = subprocess.run(["git", "commit", "-m", msg], capture_output=True, text=True, cwd=cwd)
print("GIT COMMIT STDOUT:", r_commit.stdout)
print("GIT COMMIT STDERR:", r_commit.stderr)

# Push master
r_push_m = subprocess.run(["git", "push", "origin", "master"], capture_output=True, text=True, cwd=cwd)
print("PUSH MASTER STDOUT:", r_push_m.stdout)
print("PUSH MASTER STDERR:", r_push_m.stderr)

# Push main
r_push_main = subprocess.run(["git", "push", "origin", "master:main", "--force"], capture_output=True, text=True, cwd=cwd)
print("PUSH MAIN STDOUT:", r_push_main.stdout)
print("PUSH MAIN STDERR:", r_push_main.stderr)
