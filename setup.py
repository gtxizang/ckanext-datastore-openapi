from pathlib import Path
from setuptools import setup, find_packages

HERE = Path(__file__).parent
long_description = (HERE / "README.md").read_text(encoding="utf-8")

setup(
    name="ckanext-datastore-openapi",
    version="0.1.0",
    description=(
        "OpenAPI 3.1 spec generation for CKAN DataStore resources "
        "with pg_stats introspection, caching, and DCAT 3 integration"
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gtxizang/ckanext-datastore-openapi",
    license="MIT",
    python_requires=">=3.9",
    packages=find_packages(include=["ckanext", "ckanext.*"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "ckan>=2.10",
        "dogpile.cache>=1.0",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    entry_points={
        "ckan.plugins": [
            "datastore_openapi = ckanext.datastore_openapi.plugin:DatastoreOpenapiPlugin",
        ],
    },
)
