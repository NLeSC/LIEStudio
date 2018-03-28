# MDStudio
[![Build Status](https://travis-ci.org/MD-Studio/MDStudio.svg?branch=master)](https://travis-ci.org/MD-Studio/MDStudio)

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/aff6245274f44a7991a3a25976ad6472)](https://www.codacy.com/app/tifonzafel/MDStudio?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=MD-Studio/MDStudio&amp;utm_campaign=Badge_Grade)

MDStudio is a stand-alone application featuring a web based graphical user interface.
Most of the application is written in Python. The web based GUI runs as a client side
Angular application.
    
## Docker
To make development easier we have setup a docker environment.

### Prerequisites

 * [Docker](https://www.docker.com/), that's it.

### Installation
Run the builder under bash:

    >> ./build.sh

### Usage
To use the docker environment you have to start the container:

    >> ./start.sh

To start a **development** container use:

    >> ./start-dev.sh

This command will spin up the complete environment including MongoDB, and logs in into the 
container. When you want to exit this mode just use `>> exit` to exit. Containers can be
stopped using:

    >> ./stop.sh

### IDE Integration

#### Pycharms
Go to `File > Project Settings > Project Interpreter`, and add a remote interpreter,
and make sure it matches this screen.

![Configuration settings](docs/img/pycharm-config.png)

Note specifically:

|                      |                                                            |
|----------------------|------------------------------------------------------------|
| Interpreter path     | `/root/.local/share/virtualenvs/app-4PlAip0Q/bin/python`   |

## Manual
When you want to keep track of the whole environment for yourself, you should follow these
instructions.

### Prerequisites
The MDStudio application is written in Python and mostly self contained thanks to the
use of an in-application Python virtual environment.
The application has currently been successfully tested with Python versions: 2.7

The only external dependencies are:

 * [MongoDB](https://www.mongodb.com) - A NoSQL database.
 * [Pipenv](https://github.com/kennethreitz/pipenv) - A python virtual environment manager.
 * [Redis](https://redis.io/) - A fast caching layer.

### Installation
Install the virtual environment with:

    >> pipenv install --skip-lock --dev --sequential

You can install the virtual environment in your directory by enabling the environment variable:
```
PIPENV_VENV_IN_PROJECT = 1
```
For more information see [this](https://docs.pipenv.org/advanced.html#custom-virtual-environment-location).
  
### Usage
The application is started on the command line as:

    >> pipenv shell
    >> python .

## Creating components

### Directory structure
A component should have (as a minimum) the following structure

    components/my_component/
        my_component/
            schemas/
                endpoints/
                    some-endpoint.request.v1.json
                    some-endpoint.response.v1.json
                resources/
                    some-resource.v1.json
            __init__.py
            __main__.py
            application.py
        Pipfile
        settings.yml
        setup.py
        
- The `setup.py` contains the dependencies and a short description of the component.
- The `settings.yml` contains the default settings of the component. They can be overwritten by locally creating a `.settings.yml`.
- The `Pipfile` is used for creating a virtual environment inside the docker container that contains both the dependencies from `setup.py`, and the `mdstudio` library.
- The `__init__.py` is necessary for Python to recognize it as a package. It should ideally remain empty.
- The `__main__.py` contains the startup script for the component.
- The `application.py` contains the Component definition with its endpoints.
- The `schemas` folder contains json-schemas for checking the request and response from the endpoints defined in the component.

A minimal example of a component is given in the Echo component (components lie_echo).

### Endpoint registration
This component registers a single endpoint:

    @endpoint('hello', 'hello-request', 'hello-response')
    def hello(self, request, claims):
        return_time = now()
        request['message']['sendTime'] = send_time = from_utc_string(request['message']['sendTime'])

        if self.component_config.settings['printInEndpoint']:
            pprint(request)

        self.report_delay('User -> Component', return_time - send_time)

        request['returnTime'] = return_time

        return request

This endpoint is callable at the (full) uri: `mdgroup.echo.endpoint.hello`. This is also done in the `on_run` of the component, with a small delay.
The `@endpoint({uri}, {input-schema}, {output-schema})` definition does the following: it prefixes the uri to obtain the full uri `{vendor}.{component}.endpoint.{uri}` for registration.
When called, it verifies the permissions, validates the request with the `{input-schema}`, and validating the output with the `{output-schema}`.
The input schema is required, but could also have been defined inline, for example: `{'type': 'null'}` if the function does not require input (status endpoints). The output schema is not required, but defaults to `{'type': 'null'}`, so that it only allows functions without output.

These input and output schemas relieve your Component code from validating input. A guide of the basics of json-schemas is given [here](https://spacetelescope.github.io/understanding-json-schema/).

### Authorization
Authorization happens in two phases: in the core of the MDStudio application, and in the component that is called. For this purpose, the `authorize request` should be overridden like so:

    def authorize_request(self, uri, claims):
        # If you were allowed to call this in the first place, I will assume you are authorized
        return True

Custom claims can be made by the caller of your endpoint. These claims are signed and verified by the Authorization component automatically,
so that you are sure that they are not spoofed once you receive them.
You can then use them for custom authorization.

### Calling methods
In the example, the component calls itself once the registration is complete, by scheduling the call two seconds later with `call_later(2, call_hello)`.

    @chainable
    def call_hello(self):
        with self.group_context('mdgroup'):
            send_time = now()
            response = yield self.call('mdgroup.echo.endpoint.hello', {
                'message': {
                    'greeting': 'Hello World!',
                    'sendTime': send_time
                }
            })

A few things happen here: the context is switched from the default user context for calling to the group context of `mdgroup`.
This makes sure that you are authorized to call the endpoint as the given group, and sign the group into your claims.
The context is automatically restored after the indented `with` codeblock, even if the call fails.

#### Chainable
The `@chainable` decorator is an extension of (and should therefore be preferred over) the previously used `@inlineCallbacks`.
Functions wrapped in chainable support the `yield` syntax, as well as chaining methods with the result.
For example:

    # call('some.uri') result:
    # {
    #     'property': {
    #         'nested-property': {
    #             'value': 0
    #         }
    #     }
    # }
    
    # old style
    @inlineCallbacks
    def first_method():
        result = yield call('some.uri')
        returnValue(result['property'])

    @inlineCallbacks
    def second_method():
        result = yield first_method()
        calculated_value = result['nested-property'] + 1
        returnValue(calculated_value)


    # new style
    def first_method():
        result = call('some.uri')
        return result['property']  # this is chained to the Chainable result of `call`

    @chainable
    def second_method()
        calculated_value = (yield first_method()['nested-property']) + 1

        return_value(calculated_value)

This example is not to promote the style of `call` without `yield`, but to demonstrate the power of chaining. 
It is now not always necessary to use the decorator, even when we need to extract something from a deferred result!
Everything you need for this is defined in the `mdstudio` library.

### Running your component
For running your component, you need a (very small) `__main__.py` script, containing the following.

    from mdstudio.runner import main
    from my_component.application import MyComponent

    if __name__ == '__main__':
        main(MyComponent)

That's it! You can now install your component and run it!

    >>> pipenv shell
    >>> pip install -e components/my_component
    >>> python -m my_component

## Settings
Since the components are started as micro-services, there is no global configuration variable. 
For component-specific configuration and session configuration (details for automatic login), you can use all or any of
- settings.json
- .settins.json
- settings.yml
- .settings.yml

They are loaded in this order, and each next file overwrites and extends settings from the previous. 
These can also be overridden for development by
- settings.dev.json
- .settings.dev.json
- settings.dev.yml
- .settings.dev.yml

The dot-prefixed settings are not committed, and should be used for production settings that should not be shared through git.

The settings are loaded into the `ComponentSession` in the variable `self.component_config`, with three sections: `static`, `session`, `settings`.
The `session` section is used for session-specific configuration, such as login details
The `static` section is used for vendor-defined (the component developer) settings.
The `settings` section is intended for component settings that are variable and can be changed.
