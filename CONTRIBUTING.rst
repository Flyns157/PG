Contributing
============

Any contributions are welcome and appreciated!

Types of Contributions
----------------------

Report Bugs
~~~~~~~~~~~

Report bugs at https://github.com/Flyns157/PG/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

Fix Bugs
~~~~~~~~

Look through the GitHub issues for bugs. Anything tagged with **bug** and **help wanted** is open to whoever wants to implement it.

Implement Features
~~~~~~~~~~~~~~~~~~

Look through the issues for features. Anything tagged with **enhancement**
and **help wanted** is open to whoever wants to implement it.

Write Documentation
~~~~~~~~~~~~~~~~~~~

PG could always use more documentation, whether as part of the
official PG docs, in docstrings, or even on the web in blog posts,
articles, and such.

Documentation Style
:::::::::::::::::::

This project uses `Google Python Documentation Style <https://google.github.io/styleguide/pyguide.html>`_.

**Note**:

- For documenting endpoint functions, please use ``\f`` in your documentation to truncate the output used for OpenAPI at this point.

Please check `Advanced description from docstring <https://fastapi.tiangolo.com/advanced/path-operation-advanced-configuration/#advanced-description-from-docstring>`_ for more details.


Submit Feedback
~~~~~~~~~~~~~~~

The best way to send feedback is to file an issue at https://github.com/Flyns157/PG/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.

Get Started!
------------

Ready to contribute? Here's how to set up `pg` for local development.

1. Fork the `pg` repo on GitHub.
2. Clone your fork locally::

    $ git clone git@your_repo_url.git

3. Install your local copy into a virtualenv. Assuming you have virtualenv installed, this is how you set up your fork for local development::

    $ python -m virtualenv pg-venv
    $ source pg-venv/bin/activate
    $ cd pg/

   Now you can install `pg` in develop mode in your virtual environment::

    $ python setup.py develop

   or::

    $ pip install -e .

4. Create a branch for local development::

    $ git checkout -b name-of-your-bugfix-or-feature

   Now you can make your changes locally.

5. When you're done making changes, check that your changes pass all linting checks and the
   tests, including testing other Python versions with tox::

    $ make flake8
    $ make mypy
    $ make bandit
    $ ./docker-compose.sh build test_pg
    $ ./docker-compose.sh run --rm test_pg
    $ ./docker-compose.sh stop && ./docker-compose.sh rm -f && ./docker-compose.sh clean
    $ tox

   To get **flake8**, **mypy**, **bandit** and **tox**, just pip install them into your virtualenv.

6. Run the API service locally via `docker-compose`_ to check your changes::

    $ ./docker-compose.sh build pg
    $ ./docker-compose.sh run --service-ports --rm pg

   * The service could also run in detached mode with flag ``-d``.
   * When the `docker-compose`_ starts the service, it will execute the SQL
     script ``./docker/init.sql`` to create a superuser in ``AuthUser`` table.
     (The credential of the default user is [username: "dummy", password: "123456"])
   * To stop and remove the running containers, please execute::

     $ ./docker-compose.sh stop && ./docker-compose.sh rm -f && ./docker-compose.sh clean

7. Commit your changes and push your branch to GitHub::

    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature

8. Submit a pull request through the GitHub website.

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring, and add the
   feature to the list in README.rst.

Deploying
---------

Assume that bump2version_ is installed. To deploy the package, just run::

    $ bump2version patch  # possible: major / minor / patch
    $ git push
    $ git push --tags

Github Actions will do the rest.

.. _bump2version: https://github.com/c4urself/bump2version
.. _docker-compose: https://docs.docker.com/compose/