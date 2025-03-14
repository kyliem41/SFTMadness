# sftMadness
## ALL COMMANDS TO RUN ARE IN 'QUOTES'

- all in the backend (cd /sftBack/sftMadness)

- install AWS CLI and AWS Sam:
https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html - aws install link
https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html - sam install link

- configure AWS Sam profile to connect to AWS account under the admin profile:
aws configure --profile admin
  - this will ask you to procide an access key - this may change if you update the admin role in AWS - you will find the new one in AWS IAM -> users -> admin
  - current access key: AKIA5G2VGZQF3S4I2SOQ
  - then will ask for a secret access key - can also update, found in the same place
  - current secret key: wSEy3vQn6ead0EzyONPgNimigLK9mnw45z/WTKdT

- install any other needed dependencies on your machine, these can all be found in the requirements.txt file (except for tiktoken)

- checks if template.yaml file is valid (reports any issues)
  - always run this before building or deploying
'sam validate'

- builds the project, you must have Docker desktop installed and running - this will build an image in Docker
'sam build --use-container'

- deploys project to API Gateway (should always use admin profile)
'sam deploy'  | 'sam deploy --guided' (disable rollback => n)

- deploy with admin IAM Role:
'aws configure --profile admin'
'sam deploy --profile admin'

- 'sam deploy --guided' - will ask additional questions
inputs will all be the same as whats presented in the [brackets]: copy and paste these one at a time and enter
then for the y/n questions, answer Y to the first few, N to disabling rollback, then again copy the [] to enter 'samconfig.toml' as the output dir
then press enter twice for the last two settings, after this it will start to deploy and you should see a green success message at the end 

- if a stack is unable to update or create (failing or in update_rollback state)
'aws cloudformation delete-stack --stack-name sftMadness'

- describes status of stack if deleting, updated, or deletion failed, etc
'aws cloudformation describe-stacks --stack-name sftMadness --query 'Stacks[0].StackStatus''

- better debugging status for stack
- if delete fails => find out why
'aws cloudformation describe-stack-events --stack-name sftMadness --query 'StackEvents[?ResourceStatus==`DELETE_FAILED`].[LogicalResourceId,ResourceStatusReason]''

- if delete fails => retain security group and try delete again
'aws cloudformation delete-stack --stack-name sftMadness --retain-resources LambdaSecurityGroup'

- remove any built dependencies from dependency layer
- use this if having any trouble with building, this will clear the cache and usually helps solve the issue
'rm -rf .aws-sam/build'

- force remove S3 bucket to allow deletion of stack
- if delete fails again, try force removing the S3 bucket
'aws s3 rb s3://sftmadness-files-us-east-2-908027415563 --force'
  - this is only an example for one of the S3 buckets, there are two
  - be sure to grab the exact iD from the S3 buckets in AWS and by getting the Id from the correct bucket you want to delete

- download dependencies from requirement.txt to layers folder
  - not needed, but this is another way to require dependencies if the build is not working
  - you will need to make another dir in the project to match this
'pip3 install -r requirements.txt -t layers/dependencies/python'





- in the frontend (cd /sftFront/sftmadnessfront), you will need to install
  - react native
  - aws amplify
  - and mui : 'npm install @mui/material @mui/icons-material @emotion/react @emotion/styled'



This project contains source code and supporting files for a serverless application that you can deploy with the SAM CLI. It includes the following files and folders.

- hello_world - Code for the application's Lambda function.
- events - Invocation events that you can use to invoke the function.
- tests - Unit tests for the application code. 
- template.yaml - A template that defines the application's AWS resources.

The application uses several AWS resources, including Lambda functions and an API Gateway API. These resources are defined in the `template.yaml` file in this project. You can update the template to add AWS resources through the same deployment process that updates your application code.

If you prefer to use an integrated development environment (IDE) to build and test your application, you can use the AWS Toolkit.  
The AWS Toolkit is an open source plug-in for popular IDEs that uses the SAM CLI to build and deploy serverless applications on AWS. The AWS Toolkit also adds a simplified step-through debugging experience for Lambda function code. See the following links to get started.

* [CLion](https://docs.aws.amazon.com/toolkit-for-jetbrains/latest/userguide/welcome.html)
* [GoLand](https://docs.aws.amazon.com/toolkit-for-jetbrains/latest/userguide/welcome.html)
* [IntelliJ](https://docs.aws.amazon.com/toolkit-for-jetbrains/latest/userguide/welcome.html)
* [WebStorm](https://docs.aws.amazon.com/toolkit-for-jetbrains/latest/userguide/welcome.html)
* [Rider](https://docs.aws.amazon.com/toolkit-for-jetbrains/latest/userguide/welcome.html)
* [PhpStorm](https://docs.aws.amazon.com/toolkit-for-jetbrains/latest/userguide/welcome.html)
* [PyCharm](https://docs.aws.amazon.com/toolkit-for-jetbrains/latest/userguide/welcome.html)
* [RubyMine](https://docs.aws.amazon.com/toolkit-for-jetbrains/latest/userguide/welcome.html)
* [DataGrip](https://docs.aws.amazon.com/toolkit-for-jetbrains/latest/userguide/welcome.html)
* [VS Code](https://docs.aws.amazon.com/toolkit-for-vscode/latest/userguide/welcome.html)
* [Visual Studio](https://docs.aws.amazon.com/toolkit-for-visual-studio/latest/user-guide/welcome.html)

## Deploy the sample application

The Serverless Application Model Command Line Interface (SAM CLI) is an extension of the AWS CLI that adds functionality for building and testing Lambda applications. It uses Docker to run your functions in an Amazon Linux environment that matches Lambda. It can also emulate your application's build environment and API.

To use the SAM CLI, you need the following tools.

* SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
* [Python 3 installed](https://www.python.org/downloads/)
* Docker - [Install Docker community edition](https://hub.docker.com/search/?type=edition&offering=community)

To build and deploy your application for the first time, run the following in your shell:

```bash
sam build --use-container
sam deploy --guided
```

The first command will build the source of your application. The second command will package and deploy your application to AWS, with a series of prompts:

* **Stack Name**: The name of the stack to deploy to CloudFormation. This should be unique to your account and region, and a good starting point would be something matching your project name.
* **AWS Region**: The AWS region you want to deploy your app to.
* **Confirm changes before deploy**: If set to yes, any change sets will be shown to you before execution for manual review. If set to no, the AWS SAM CLI will automatically deploy application changes.
* **Allow SAM CLI IAM role creation**: Many AWS SAM templates, including this example, create AWS IAM roles required for the AWS Lambda function(s) included to access AWS services. By default, these are scoped down to minimum required permissions. To deploy an AWS CloudFormation stack which creates or modifies IAM roles, the `CAPABILITY_IAM` value for `capabilities` must be provided. If permission isn't provided through this prompt, to deploy this example you must explicitly pass `--capabilities CAPABILITY_IAM` to the `sam deploy` command.
* **Save arguments to samconfig.toml**: If set to yes, your choices will be saved to a configuration file inside the project, so that in the future you can just re-run `sam deploy` without parameters to deploy changes to your application.

You can find your API Gateway Endpoint URL in the output values displayed after deployment.

## Use the SAM CLI to build and test locally

Build your application with the `sam build --use-container` command.

```bash
sftMadness$ sam build --use-container
```

The SAM CLI installs dependencies defined in `hello_world/requirements.txt`, creates a deployment package, and saves it in the `.aws-sam/build` folder.

Test a single function by invoking it directly with a test event. An event is a JSON document that represents the input that the function receives from the event source. Test events are included in the `events` folder in this project.

Run functions locally and invoke them with the `sam local invoke` command.

```bash
sftMadness$ sam local invoke HelloWorldFunction --event events/event.json
```

The SAM CLI can also emulate your application's API. Use the `sam local start-api` to run the API locally on port 3000.

```bash
sftMadness$ sam local start-api
sftMadness$ curl http://localhost:3000/
```

The SAM CLI reads the application template to determine the API's routes and the functions that they invoke. The `Events` property on each function's definition includes the route and method for each path.

```yaml
      Events:
        HelloWorld:
          Type: Api
          Properties:
            Path: /hello
            Method: get
```

## Add a resource to your application
The application template uses AWS Serverless Application Model (AWS SAM) to define application resources. AWS SAM is an extension of AWS CloudFormation with a simpler syntax for configuring common serverless application resources such as functions, triggers, and APIs. For resources not included in [the SAM specification](https://github.com/awslabs/serverless-application-model/blob/master/versions/2016-10-31.md), you can use standard [AWS CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-template-resource-type-ref.html) resource types.

## Fetch, tail, and filter Lambda function logs

To simplify troubleshooting, SAM CLI has a command called `sam logs`. `sam logs` lets you fetch logs generated by your deployed Lambda function from the command line. In addition to printing the logs on the terminal, this command has several nifty features to help you quickly find the bug.

`NOTE`: This command works for all AWS Lambda functions; not just the ones you deploy using SAM.

```bash
sftMadness$ sam logs -n HelloWorldFunction --stack-name "sftmadness" --tail
```

You can find more information and examples about filtering Lambda function logs in the [SAM CLI Documentation](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-logging.html).

## Tests

Tests are defined in the `tests` folder in this project. Use PIP to install the test dependencies and run tests.

```bash
sftMadness$ pip install -r tests/requirements.txt --user
# unit test
sftMadness$ python -m pytest tests/unit -v
# integration test, requiring deploying the stack first.
# Create the env variable AWS_SAM_STACK_NAME with the name of the stack we are testing
sftMadness$ AWS_SAM_STACK_NAME="sftmadness" python -m pytest tests/integration -v
```

## Cleanup

To delete the sample application that you created, use the AWS CLI. Assuming you used your project name for the stack name, you can run the following:

```bash
sam delete --stack-name "sftmadness"
```

## Resources

See the [AWS SAM developer guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html) for an introduction to SAM specification, the SAM CLI, and serverless application concepts.

Next, you can use AWS Serverless Application Repository to deploy ready to use Apps that go beyond hello world samples and learn how authors developed their applications: [AWS Serverless Application Repository main page](https://aws.amazon.com/serverless/serverlessrepo/)