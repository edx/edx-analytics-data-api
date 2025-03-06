# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/edx/edx-analytics-data-api/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                                                  |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|-------------------------------------------------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| analytics\_data\_api/\_\_init\_\_.py                                                  |        0 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/constants/\_\_init\_\_.py                                        |        0 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/constants/country.py                                             |       18 |        0 |        6 |        0 |    100% |           |
| analytics\_data\_api/constants/engagement\_events.py                                  |       12 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/constants/enrollment\_modes.py                                   |        8 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/constants/genders.py                                             |        5 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/constants/learner.py                                             |        2 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/docker\_gunicorn\_configuration.py                               |        6 |        6 |        0 |        0 |      0% |      6-13 |
| analytics\_data\_api/management/\_\_init\_\_.py                                       |        0 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/management/commands/\_\_init\_\_.py                              |        0 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/management/commands/generate\_data.py                            |      165 |        3 |       46 |        0 |     99% |   300-307 |
| analytics\_data\_api/management/commands/generate\_fake\_course\_data.py              |       40 |        5 |        6 |        2 |     80% | 71-74, 84 |
| analytics\_data\_api/management/commands/generate\_stage\_course\_data.py             |       38 |        0 |        6 |        0 |    100% |           |
| analytics\_data\_api/management/commands/set\_api\_key.py                             |       25 |        0 |        6 |        0 |    100% |           |
| analytics\_data\_api/management/commands/tests/test\_generate\_fake\_course\_data.py  |       13 |        0 |        2 |        0 |    100% |           |
| analytics\_data\_api/management/commands/tests/test\_generate\_stage\_course\_data.py |       42 |        0 |       18 |        0 |    100% |           |
| analytics\_data\_api/middleware.py                                                    |       68 |        3 |        4 |        0 |     96% |69, 73, 77 |
| analytics\_data\_api/models.py                                                        |        0 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/renderers.py                                                     |       41 |        0 |       16 |        0 |    100% |           |
| analytics\_data\_api/tests/\_\_init\_\_.py                                            |        0 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/tests/test\_middleware.py                                        |       18 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/tests/test\_renderers.py                                         |       37 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/tests/test\_throttles.py                                         |       36 |        0 |        2 |        0 |    100% |           |
| analytics\_data\_api/tests/test\_utils.py                                             |       86 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/throttles.py                                                     |       13 |        0 |        2 |        0 |    100% |           |
| analytics\_data\_api/urls.py                                                          |        5 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/utils.py                                                         |       83 |       14 |       12 |        1 |     84% |23-25, 86-88, 177->179, 210-221, 229 |
| analytics\_data\_api/v0/\_\_init\_\_.py                                               |        0 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/v0/apps.py                                                       |        3 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/v0/exceptions.py                                                 |       28 |        2 |        0 |        0 |     93% |     20-21 |
| analytics\_data\_api/v0/models.py                                                     |      181 |        1 |        0 |        0 |     99% |       257 |
| analytics\_data\_api/v0/serializers.py                                                |      287 |       19 |       32 |        1 |     94% |160-161, 169, 220-224, 257-261, 373, 376, 379, 382, 487, 490, 493, 496 |
| analytics\_data\_api/v0/tests/\_\_init\_\_.py                                         |        0 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/v0/tests/test\_models.py                                         |       21 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/v0/tests/test\_serializers.py                                    |       40 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/v0/tests/test\_urls.py                                           |       18 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/v0/tests/utils.py                                                |       20 |        0 |        6 |        0 |    100% |           |
| analytics\_data\_api/v0/tests/views/\_\_init\_\_.py                                   |       94 |        1 |       14 |        0 |     99% |        96 |
| analytics\_data\_api/v0/tests/views/test\_course\_summaries.py                        |      144 |        0 |       14 |        0 |    100% |           |
| analytics\_data\_api/v0/tests/views/test\_courses.py                                  |      510 |        0 |       30 |        0 |    100% |           |
| analytics\_data\_api/v0/tests/views/test\_enterprise\_learner\_engagements.py         |       39 |        0 |        2 |        0 |    100% |           |
| analytics\_data\_api/v0/tests/views/test\_problems.py                                 |       95 |        0 |        2 |        0 |    100% |           |
| analytics\_data\_api/v0/tests/views/test\_programs.py                                 |       68 |        1 |       16 |        1 |     98% |        47 |
| analytics\_data\_api/v0/tests/views/test\_utils.py                                    |       32 |        2 |        0 |        0 |     94% |     27-28 |
| analytics\_data\_api/v0/tests/views/test\_videos.py                                   |       31 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/v0/urls/\_\_init\_\_.py                                          |        5 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/v0/urls/course\_summaries.py                                     |        4 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/v0/urls/courses.py                                               |        9 |        0 |        2 |        0 |    100% |           |
| analytics\_data\_api/v0/urls/learners.py                                              |        6 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/v0/urls/problems.py                                              |        8 |        0 |        2 |        0 |    100% |           |
| analytics\_data\_api/v0/urls/programs.py                                              |        4 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/v0/urls/videos.py                                                |        8 |        0 |        2 |        0 |    100% |           |
| analytics\_data\_api/v0/views/\_\_init\_\_.py                                         |       57 |        1 |        6 |        0 |     98% |       146 |
| analytics\_data\_api/v0/views/course\_summaries.py                                    |      116 |        0 |       44 |        0 |    100% |           |
| analytics\_data\_api/v0/views/courses.py                                              |      268 |        4 |       58 |        5 |     97% |133->136, 275->278, 676-679, 688, 702->692 |
| analytics\_data\_api/v0/views/learners.py                                             |       37 |        0 |        4 |        0 |    100% |           |
| analytics\_data\_api/v0/views/problems.py                                             |       65 |        1 |       18 |        1 |     98% |        88 |
| analytics\_data\_api/v0/views/programs.py                                             |       21 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/v0/views/utils.py                                                |       20 |        0 |        4 |        0 |    100% |           |
| analytics\_data\_api/v0/views/videos.py                                               |       11 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/v1/\_\_init\_\_.py                                               |        0 |        0 |        0 |        0 |    100% |           |
| analytics\_data\_api/v1/urls.py                                                       |       11 |        0 |        2 |        0 |    100% |           |
|                                                                             **TOTAL** | **3022** |   **63** |  **384** |   **11** | **98%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/edx/edx-analytics-data-api/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/edx/edx-analytics-data-api/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/edx/edx-analytics-data-api/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/edx/edx-analytics-data-api/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fedx%2Fedx-analytics-data-api%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/edx/edx-analytics-data-api/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.