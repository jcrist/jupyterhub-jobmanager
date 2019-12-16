from setuptools import setup

setup(
    name="jupyterhub-jobmanager",
    version="0.0.1",
    license="BSD",
    maintainer="Jim Crist",
    maintainer_email="jiminy.crist@gmail.com",
    description="Manage job deployments on JupyterHub",
    packages=["jupyterhub_jobmanager"],
    python_requires=">=3.5",
    entry_points={
        "console_scripts": [
            "jupyterhub-jobmanager = jupyterhub_jobmanager.app:main",
        ]
    },
    zip_safe=False,
)
