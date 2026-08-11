import subprocess

esbuild = r"C:\Users\Keerthana\.gemini\antigravity\scratch\socialpilot\frontend\node_modules\@esbuild\win32-x64\esbuild.exe"
cmd = [
    esbuild,
    "src/main.jsx",
    "--bundle",
    "--outfile=dist/assets/index-C9LTWJV2.js",
    "--loader:.js=jsx",
    "--loader:.jsx=jsx",
    '--define:process.env.NODE_ENV="production"'
]

res = subprocess.run(cmd, cwd=r"C:\Users\Keerthana\.gemini\antigravity\scratch\socialpilot\frontend", capture_output=True, text=True)
print("STDOUT:", res.stdout)
print("STDERR:", res.stderr)
print("Return code:", res.returncode)
