
import os
import sys
import shutil
import time
import git_lc_agent

# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

python = sys.executable

t_start = time.time()
os.system(f'"{python}" -m build')
t_end = time.time()
print(f"build time: {t_end - t_start}")

t_start = time.time()
os.system(f'"{python}" -m twine upload dist/* --verbose')
t_end = time.time()
print(f"upload time: {t_end - t_start}")

# if os.path.exists("dist"):
#     shutil.rmtree("dist")


print(time.strftime("%Y-%m-%d %H:%M:%S"))

time.sleep(1000000)

