import newrelic.jenkins.extensions

String organization = 'python-agent'
String repoGHE = 'python_agent'
String repoFull = "${organization}/${repoGHE}"
String testPrefix = "${organization}-tools"
String integTestSuffix = "__integration-test"
String unitTestSuffix = "__unit-test"
String slackChannel = '#python-dev'


// Views for any tool-like jobs

use(extensions) {
    view('PY_Tools', 'A view for some tools',
         "(${testPrefix}.*)|(python_agent-dsl-seed)")

    // python_agent-dsl-seed job
    baseJob('python_agent-dsl-seed') {
        label('master')
        repo(repoFull)
        branch('develop')

        configure {
            description("A job to create other Jenkins DSL defined jobs in the ${repoGHE} repo.")

            triggers {
                githubPush()
            }

            // block on any RUNNING job (not queued)
            blockOnJobs('.*', 'GLOBAL', 'DISABLED')

            steps {
                reseedFrom('jenkins/*.groovy')
            }

            slackQuiet(slackChannel)
        }
    }

    baseJob("${testPrefix}-Packnsend-Build-and-Push") {
        label('py-ec2-linux')
        repo(repoFull)
        branch('${GIT_BRANCH}')

        configure {
            description('A job to build packnsend images then push them to ' +
                    "the repo. Once complete, consider running the ${testPrefix}-" +
                    'Reset-Nodes job to reset all nodes. (They won\'t get the ' +
                    'new images if you don\'t)')

            parameters {
                stringParam('GIT_BRANCH', 'develop', '')
            }

            steps {
                environmentVariables {
                    env('DOCKER_HOST', 'unix:///var/run/docker.sock')
                }
                shell('./jenkins/scripts/packnsend-buildnpush.sh')
            }

            slackQuiet(slackChannel)
        }
    }

    baseJob("${testPrefix}-build-pip-cache") {
        label('py-ec2-linux')
        repo(repoFull)
        branch('${GIT_BRANCH}')

        configure {
            description('A job to build the PIP cache image and push it to ' +
                    'the repo. Once complete, the reset nodes job should be run.')

            triggers {
                // run daily on cron
                cron('H 0 * * 1-5')
            }

            parameters {
                stringParam('GIT_BRANCH', 'develop', "Generally, we don't want " +
                        "to change this setting. This parameter is here in case " +
                        "we want to rebuild the cache on a branch (for a PR, for " +
                        "example)")
            }

            steps {
                environmentVariables {
                    env('DOCKER_HOST', 'unix:///var/run/docker.sock')
                }
                shell('./jenkins/scripts/packnsend-build-pip-cache.sh')
            }

            slackQuiet(slackChannel)
        }
    }

    baseJob("${testPrefix}-Reset-Nodes") {
        repo(repoFull)
        branch('${GIT_BRANCH}')

        configure {
            description('A job to reset all ec2 nodes. It will perform a ' +
                        'packnsend pull then restart all containers. ' +
                        '<h3>Don\'t forget to wake up all EC2 nodes before ' +
                        'running this job!</h3>')

            triggers {
                upstream("${testPrefix}-build-pip-cache")
                upstream("${testPrefix}-Packnsend-Build-and-Push")
            }

            concurrentBuild true
            logRotator { numToKeep(10) }

            // block on any RUNNING job (not queued)
            blockOnJobs("(.*${integTestSuffix})|(.*${unitTestSuffix})", 'GLOBAL', 'DISABLED')

            parameters {
                stringParam('GIT_BRANCH', 'develop',
                    'The branch on which to find the scripts to reset the ' +
                    'nodes. Most likely you won\'t have to change this.')
                labelParam('NODE_NAME') {
                    defaultValue('py-ec2-linux')
                    description('The label of the nodes to perform the reset. (hint: the ' +
                        'label of our ec2 nodes is \"py-ec2-linux\") This job will ' +
                        'be run once on each node.')
                    allNodes('allCases', 'AllNodeEligibility')
                }
            }

            steps {
                environmentVariables {
                    env('DOCKER_HOST', 'unix:///var/run/docker.sock')
                }
                shell('./jenkins/scripts/refresh_docker_containers.sh')
            }

            slackQuiet(slackChannel)
        }
    }
}