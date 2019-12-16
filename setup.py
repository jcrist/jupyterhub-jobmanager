from setuptools import setup

import versioneer

install_requires = ["tornado"]

setup(
    name="jupyterhub-jobmanager",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    license="BSD",
    maintainer="Jim Crist",
    maintainer_email="jiminy.crist@gmail.com",
    description="Manage job deployments on JupyterHub",
    packages=["jupyterhub_jobmanager"],
    python_requires=">=3.5",
    install_requires=install_requires,
    entry_points={
        "console_scripts": ["jupyterhub-jobmanager = jupyterhub_jobmanager.app:main"]
    },
    zip_safe=False,
)
