import subprocess

scripts = [
    "post_analysis.py",
    "degree_analysis.py",
    "clustering_analysis.py",
    "feed_analysis.py",
    "latent_opinion_analysis.py",
    "opinion_variance_analysis.py",
    "opinion_change_gif_maker.py"
]

for script in scripts:
    print(f"\n now processing : {script}")
    result = subprocess.run(["python3", "python/scripts/" + script], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"error occurred: {script}")
        print(result.stderr)
        break
    else:
        print(f"finish: {script}")
        print(result.stdout)
