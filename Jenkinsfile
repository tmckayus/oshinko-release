/*
* Credentials Required:
*
* github-automation-user
* github-automation-email
* github-user-auth-token
* dh_trigger_token_openshift_spark
* dh_trigger_token_sti_scala
* dh_trigger_token_sti_pysprk
* dh_trigger_token_sti_java
* dh_trigger_token_oc_proxy
* dh_trigger_token_oshinko_webui
* dh_trigger_token_oshinko_cli
*
*/


""" Parameters required for the build. """
Map<String, String> BUILD_PARAMETERS = [
        "SPARK_VERSION": SPARK_VERSION,
        "OSHINKO_VERSION": OSHINKO_VERSION,
        "cliReleaseNotes": cliReleaseNotes,
        "stiReleaseSummary": stiReleaseSummary,
        "githubRepositories": githubRepositories,
        "dockerhubRepositories": dockerhubRepositories,
        "autobuildStageRetryCount": autobuildStageRetryCount,
        "repoWatchInterval": repoWatchInterval,
        "watchRetryCount": watchRetryCount,
        "githubRepoOwner": githubRepoOwner,
        "dockerhubRepoOwner": dockerhubRepoOwner,
        "stiMergeToBranch": stiMergeToBranch,
]

private void prepareWorkspace(String githubDirectory) {

    // wipeout workspace
    deleteDir()

    dir(githubDirectory) {
        checkout scm
    }

    sh('concreate --version')
}

private void repoCtrl() { repoCtrl(-1) }

// Note stage is not a jenkins stage, but an actual step within the repoctrl script
private void repoCtrl(int stage){
    String additionalArgs = " "
    if (stage >= 0) { additionalArgs += " -s ${stage} " as String }

    dir(GH_RELEASE_DIR) {
        tmpdir = sh returnStdout: true, script: 'echo `mktemp -d`'
        tmpdir = tmpdir.trim()
        try {
            GString args = "${GH_REPO_OWNER} ${GH_REPO} ${GH_AUTH_TOKEN} ${tmpdir} ${OSHINKO_VERSION} " +
                    "${CURRENT_PROJECT} ${GH_USER} ${GH_USER_EMAIL}"
            sh("${REPO_CTRL}${additionalArgs}${args}")
        } catch (err) {
            throw err
        } finally {
            // Delete tmpdir
            dir(tmpdir){ deleteDir() }
        }
    }
}

private void watchAutoBuildStage(String sourceTag, String credentialsId){
    watchAutoBuildStage(sourceTag, "", credentialsId)
}

private void watchAutoBuildStage(String sourceTag, String sourceBranch, String credentialsId){
    stage("watch-autobuilds: ${CURRENT_PROJECT}") {
        retry(STAGE_RETRY_COUNT as Integer) {
            dir(GH_RELEASE_DIR) {
                withCredentials([string(credentialsId: "${credentialsId}", variable: 'TRIGGER_TOKEN')]) {
                    String additionalArgs = ""
                    if(sourceBranch){ additionalArgs += " -b ${sourceBranch}" as String }
                    if(sourceTag){ additionalArgs += " -t ${sourceTag}" as String }
                    try {
                        sh("${BUILD_WATCHER} ${DH_REPO_OWNER}/${DH_REPO} ${TRIGGER_TOKEN} " +
                                "-r ${RETRY_COUNT} " +
                                "-i ${INTERVAL}" +
                                "${additionalArgs}")
                    } catch (err) {
                        sleep(time: 5, unit: 'SECONDS')
                        throw err
                    }
                }
            }
        }
    }
}

private void validateParameters(Map<String, String> ghRepos, Map<String, String> dhRepos, Map<String, String> parameters) {
    parameters.each{ p, value ->
        if(!value){
            error "${p} parameter not specified"
        }
    }

    String[] ghProjects = ['openshift-spark', 'oshinko-cli', 'oshinko-webui', 'oshinko-s2i', 'oc-proxy']

    for(String project in ghProjects){
        if(!ghRepos.containsKey(project)){
            error "${project} key was not specified for github repository parameter."
        }
    }

    String[] dhProjects = ['openshift-spark', 'oshinko-cli', 'oshinko-webui',
                           'oc-proxy', 'oshinko-s2i-scala',
                           'oshinko-s2i-pyspark', 'oshinko-s2i-java']

    for(String project in dhProjects){
        if(!dhRepos.containsKey(project)){
            error "${project} key was not specified for dockerhub repository parameter."
        }
    }

}

private Map<String, String> parseReposParameter(String data){
    if(!data){
        error "Repos parameter is empty, please re-do the build with all required parameters."
    }
    echo data
    String repos = "[${data.trim()}]" as String
    repos = repos.replace("\n", ", ")
    repos = repos.replaceAll (/([\w-]+)/) { m -> "\"${m[0]}\"" }

    echo repos
    return evaluate(repos) as Map<String, String>
}

Closure<String> createTag = { version -> "v${version}" as String }

String GH_REPO_OWNER = params.githubRepoOwner
String DH_REPO_OWNER = params.dockerhubRepoOwner
String STI_MERGE_TO_BRANCH = params.stiMergeToBranch
String STI_PR_TITLE = params.stiPrTitle
String STI_PR_BODY = params.stiPrBody

String DOCKERHUB_ENDPOINT = "https://hub.docker.com/r"
String GITHUB_ENDPOINT = "https://github.com"
String GH_RELEASE_DIR = "src/github.com/${GH_REPO_OWNER}/oshinko-release" as String
String STI_CI_CONTEXTS = params.stiIntegrationContexts
String STI_BASE_BRANCH = "release${OSHINKO_VERSION}" as String
String OSHINKO_CLI_JOB = params.oshinkoCliJobName

// External Scripts used
String BUILD_WATCHER = "./watch_builds.py"
String REPO_CTRL = "./util/bash_scripts/repo_ctrl.sh"
String REL_FILE_GENERATOR = "./create_release_file.py"
String REL_GENERATOR = "./git_release.py"
String PR_AND_MERGE_HANDLER = "./git_create_pr.py"

Map<String, String> GH_REPOS = parseReposParameter(params.githubRepositories as String)
Map<String, String> DH_REPOS = parseReposParameter(params.dockerhubRepositories as String)

int AUTOBUILD_STAGE_RETRY_COUNT = params.autobuildStageRetryCount
int WATCH_INTERVAL_DEFAULT = params.repoWatchInterval
int WATCH_RETRY_COUNT_DEFAULT = params.watchRetryCount

node {
    withCredentials([string(credentialsId: 'github-automation-user', variable: 'GH_USER'),
                     string(credentialsId: 'github-automation-email', variable: 'GH_USER_EMAIL'),
                     string(credentialsId: 'github-user-auth-token', variable: 'GH_AUTH_TOKEN')]) {

        withEnv(["REPO_CTRL=${REPO_CTRL}", "DH_REPO_OWNER=${DH_REPO_OWNER}",
                 "GH_REPO_OWNER=${GH_REPO_OWNER}", "GH_RELEASE_DIR=${GH_RELEASE_DIR}",
                 "REPO_CTRL=${REPO_CTRL}", "BUILD_WATCHER=${BUILD_WATCHER}",
                 "RETRY_COUNT=${WATCH_RETRY_COUNT_DEFAULT}", "INTERVAL=${WATCH_INTERVAL_DEFAULT}",
                 "STAGE_RETRY_COUNT=${AUTOBUILD_STAGE_RETRY_COUNT}",
                 "OSHINKO_CLI_JOB=${OSHINKO_CLI_JOB}"]){

            validateParameters(GH_REPOS, DH_REPOS, BUILD_PARAMETERS)
            prepareWorkspace(GH_RELEASE_DIR)

            String stageOptions = params.stageOptions
            String[] stageOptionsList = stageOptions.split(',')

            // Openshift Spark Stages
            String osProject = "openshift-spark"
            withEnv(["CURRENT_PROJECT=${osProject}", "GH_REPO=${GH_REPOS.get(osProject)}"]){
                String sourceTag
                String sourceBranch

                if('openshift-spark-github-tag-push' in stageOptionsList){
                    echo "Starting openshift-spark-github-tag-push stage...."
                    stage("update: ${CURRENT_PROJECT}") {
                        echo "Updating  ${CURRENT_PROJECT}...."
                        dir(GH_RELEASE_DIR) {
                            String tmpdir = sh returnStdout: true, script: 'echo `mktemp -d`'
                            tmpdir = tmpdir.trim()
                            try {
                                GString args = "${GH_REPO_OWNER} ${GH_REPO} ${GH_AUTH_TOKEN} ${tmpdir} ${SPARK_VERSION} " +
                                        "${CURRENT_PROJECT} ${GH_USER} ${GH_USER_EMAIL}"
                                sh(REPO_CTRL + " ${args}")
                                ghInfoFile = "${tmpdir}/project_report/gh_info.txt"
                                def exists = fileExists ghInfoFile
                                if (exists) {
                                    String file = readFile file: ghInfoFile
                                    String[] tagAndBranch = file.split()
                                    sourceTag = tagAndBranch[0]
                                    sourceBranch = tagAndBranch[1]
                                    if (!sourceBranch || !sourceTag) {
                                        throw GroovyRuntimeException("Source tag and/or branch were not successfully extracted from openshift-spark repo.")
                                    }
                                } else {
                                    throw GroovyRuntimeException('File containing github tag/branch name for openshift-spark repo not found.')
                                }
                            } catch (err) {
                                throw err
                            } finally {
                                // Delete tmpdir
                                dir(tmpdir){ deleteDir() }
                            }
                        }
                    }
                }

                if('openshift-spark-watch-autobuild' in stageOptionsList){
                    echo "Starting openshift-spark-watch-autobuild stage...."
                    withEnv(["DH_REPO=${DH_REPOS.get(CURRENT_PROJECT)}"]){
                        watchAutoBuildStage(sourceTag, sourceBranch, 'dh_trigger_token_openshift_spark')
                    }
                }
            }

            // Oshinko Cli Stages
            String cliProject = "oshinko-cli"
            withEnv(["CURRENT_PROJECT=${cliProject}", "GH_REPO=${GH_REPOS.get(cliProject)}"]) {
                if('oshinko-cli-github-create-release' in stageOptionsList){
                    echo "Starting oshinko-cli-github-create-release stage...."
                    stage("update: ${CURRENT_PROJECT}") {
                        String cliJob = "${OSHINKO_CLI_JOB}" as String

                        String tmpdir = sh returnStdout: true, script: 'echo `mktemp -d`'
                        tmpdir = tmpdir.trim()

                        try {
                            build job: cliJob, propagate: true, wait: true
                            copyArtifacts(projectName: cliJob, target: tmpdir)
                            String artifactsDir = "${tmpdir}/src/github.com/${GH_REPO_OWNER}/${GH_REPO}/bin" as String

                            String releaseBody = sh returnStdout: true, script: "echo `mktemp release_notes_XXXXXXXXX`"
                            String releaseFile = sh returnStdout: true, script: "echo `mktemp release_XXXXXXXXX`"
                            releaseBody = releaseBody.trim()
                            releaseFile = releaseFile.trim()

                            writeFile file: releaseBody, text: params.cliReleaseNotes
                            cwd = pwd()

                            // Access to release scripts
                            dir(GH_RELEASE_DIR) {
                                // Create the release file
                                sh("${REL_FILE_GENERATOR} ${cwd}/${releaseBody} ${OSHINKO_VERSION} " +
                                        "${cwd}/${releaseFile} -a ${artifactsDir}")
                                // Generate release
                                sh("${REL_GENERATOR} ${GH_REPO_OWNER}/${GH_REPO} " +
                                        "-c ${cwd}/${releaseFile} -a ${GH_AUTH_TOKEN} -u ${GH_USER}")
                            }
                            sh("rm ${releaseFile}")
                            sh("rm ${releaseBody}")
                        } finally {
                            dir(tmpdir) { deleteDir() }
                        }
                    }
                }

                if('oshinko-cli-watch-autobuild' in stageOptionsList){
                    echo "Starting oshinko-cli-watch-autobuild stage...."
                    withEnv(["DH_REPO=${DH_REPOS.get(CURRENT_PROJECT)}"]) {
                        String sourceTag = createTag(OSHINKO_VERSION)
                        watchAutoBuildStage(sourceTag, 'dh_trigger_token_oshinko_cli')
                    }
                }
            }

            // Oshinko Webui Stages
            String webuiProject = "oshinko-webui"
            withEnv(["CURRENT_PROJECT=${webuiProject}", "GH_REPO=${GH_REPOS.get(webuiProject)}"]) {
                if('oshinko-webui-github-tag-push' in stageOptionsList){
                    echo "Starting oshinko-webui-github-tag-push stage...."
                    stage("update: ${CURRENT_PROJECT}") {
                        echo "Updating ${CURRENT_PROJECT}...."
                        repoCtrl()
                    }
                }

                if('oshinko-webui-watch-autobuild' in stageOptionsList){
                    echo "Starting oshinko-webui-watch-autobuild stage...."
                    withEnv(["DH_REPO=${DH_REPOS.get(CURRENT_PROJECT)}"]) {
                        String sourceTag = createTag(OSHINKO_VERSION)
                        watchAutoBuildStage(sourceTag, 'dh_trigger_token_oshinko_cli')
                    }
                }
            }

            // Oshinko S2I Stages
            String stiProject = "oshinko-s2i"
            withEnv(["CURRENT_PROJECT=${stiProject}", "GH_REPO=${GH_REPOS.get(stiProject)}"]){
                if('oshinko-s2i-github-release-branch' in stageOptionsList){
                    echo "Starting oshinko-s2i-github-release-branch stage...."
                    stage("create release branch: ${CURRENT_PROJECT}") {
                        echo "Creating release branch for ${CURRENT_PROJECT}...."
                        repoCtrl(0)
                    }
                }

                if('oshinko-s2i-github-create-and-merge-pr' in stageOptionsList){
                    stage("create-merge-pull-request: ${CURRENT_PROJECT}") {
                        echo "Starting oshinko-s2i-github-create-and-merge-pr stage...."
                        echo "Creating pr to watch then performing merge for ${CURRENT_PROJECT}..."
                        dir(GH_RELEASE_DIR) {
                            String ghRepo = GH_REPOS.get(CURRENT_PROJECT)
                            sh("${PR_AND_MERGE_HANDLER} " +
                                    "${GH_REPO_OWNER}/${ghRepo} " +
                                    "${GH_AUTH_TOKEN} ${OSHINKO_VERSION} " +
                                    "${GH_USER} ${STI_BASE_BRANCH} " +
                                    "-hd ${STI_MERGE_TO_BRANCH} " +
                                    "-i ${INTERVAL} " +
                                    "-r ${RETRY_COUNT} " +
                                    "-s ${STI_CI_CONTEXTS} " +
                                    "-t \"${STI_PR_TITLE}\" " +
                                    "-b \"${STI_PR_BODY}\"")
                        }
                    }
                }

                if('oshinko-s2i-github-tag-push' in stageOptionsList){
                    echo "Starting oshinko-s2i-github-tag-push stage...."
                    stage("create-tag: ${CURRENT_PROJECT}") {
                        echo "Creating tag for ${CURRENT_PROJECT}..."
                        repoCtrl(1)
                    }
                }

                if('oshinko-s2i-watch-autobuild' in stageOptionsList){
                    echo "Starting oshinko-s2i-watch-autobuild stage...."
                    stage("watch-autobuilds: ${CURRENT_PROJECT}"){
                        String sourceTag = createTag(OSHINKO_VERSION)

                        parallel (
                                'java-spark': {
                                    withEnv(["DH_REPO=${DH_REPOS.get("oshinko-s2i-java")}"]) {
                                        watchAutoBuildStage(sourceTag, 'dh_trigger_token_sti_java')
                                    }
                                },
                                'py-spark': {
                                    withEnv(["DH_REPO=${DH_REPOS.get("oshinko-s2i-pyspark")}"]) {
                                        watchAutoBuildStage(sourceTag, 'dh_trigger_token_sti_pysprk')
                                    }
                                },
                                'scala-spark': {
                                    withEnv(["DH_REPO=${DH_REPOS.get("oshinko-s2i-scala")}"]) {
                                        watchAutoBuildStage(sourceTag, 'dh_trigger_token_sti_scala')
                                    }
                                }
                        )
                    }
                }

                if('oshinko-s2i-github-create-release' in stageOptionsList){
                    echo "Starting oshinko-s2i-github-create-release stage...."
                    stage("creating release: ${CURRENT_PROJECT}") {
                        echo "Creating a release for ${CURRENT_PROJECT}..."
                        dir(GH_RELEASE_DIR) {
                            // Read template rel notes
                            String template = readFile "sti-release-body-template.txt"

                            // Get body from param
                            String relSummary = params.stiReleaseSummary

                            // Replace values and write results to tmp file
                            String cliRepo = GH_REPOS.get("oshinko-cli")
                            String dhRepoScala = DH_REPOS.get("oshinko-s2i-scala")
                            String dhRepoPyspark = DH_REPOS.get("oshinko-s2i-pyspark")
                            String dhRepoJava = DH_REPOS.get("oshinko-s2i-java")

                            String scalaLn = "${DOCKERHUB_ENDPOINT}/${DH_REPO_OWNER}/${dhRepoScala}" as String
                            String pysparkLn = "${DOCKERHUB_ENDPOINT}/${DH_REPO_OWNER}/${dhRepoPyspark}"  as String
                            String javaLn = "${DOCKERHUB_ENDPOINT}/${DH_REPO_OWNER}/${dhRepoJava}"  as String
                            String oshinkoCliLn = "${GITHUB_ENDPOINT}/${GH_REPO_OWNER}/${cliRepo}/releases/tag/v${OSHINKO_VERSION}"  as String

                            template = template.replace("<<<SCALA_SPARK_LINK>>>", "[here](${scalaLn})")
                            template = template.replace("<<<PYSPARK_LINK>>>", "[here](${pysparkLn})")
                            template = template.replace("<<<JAVA_SPARK_LINK>>>", "[here](${javaLn})")
                            template = template.replace("<<<CLI_LINK>>>", "[here](${oshinkoCliLn})")
                            template = template.replace('<<<OSHINKO_VERSION>>>', OSHINKO_VERSION)
                            template = template.replace('<<<SPARK_VERSION>>>', SPARK_VERSION)
                            template = template.replace('<<<RELEASE_NOTES_BODY>>>', relSummary)

                            // create a release file, pass in path to tmp file
                            String releaseBody = sh returnStdout: true, script: "echo `mktemp release_notes_XXXXXXXXX`"
                            String releaseFile = sh returnStdout: true, script: "echo `mktemp release_XXXXXXXXX`"
                            releaseBody = releaseBody.trim()
                            releaseFile = releaseFile.trim()

                            writeFile file: releaseBody, text: template
                            String cwd = pwd()

                            // Create the release file
                            sh("${REL_FILE_GENERATOR} ${cwd}/${releaseBody} ${OSHINKO_VERSION} ${cwd}/${releaseFile}")

                            // Generate release
                            sh("${REL_GENERATOR} ${GH_REPO_OWNER}/${GH_REPO} -c  ${cwd}/${releaseFile} -a ${GH_AUTH_TOKEN} -u ${GH_USER}")

                            sh("rm ${releaseFile}")
                            sh("rm ${releaseBody}")
                        }
                    }
                }
            }

            // OC Proxy Stages
            String ocproxyProject = "oc-proxy"
            withEnv(["CURRENT_PROJECT=${ocproxyProject}", "GH_REPO=${GH_REPOS.get(ocproxyProject)}"]) {
                if('oc-proxy-github-tag-push' in stageOptionsList){
                    echo "Starting oc-proxy-github-tag-push stage...."
                    stage("update: ${CURRENT_PROJECT}") {
                        echo "Updating ${CURRENT_PROJECT}...."
                        repoCtrl()
                    }
                }

                if('oc-proxy-watch-autobuild' in stageOptionsList){
                    echo "Starting oc-proxy-watch-autobuild stage...."
                    withEnv(["DH_REPO=${DH_REPOS.get(CURRENT_PROJECT)}"]) {
                        String sourceTag = createTag(OSHINKO_VERSION)
                        watchAutoBuildStage(sourceTag, 'dh_trigger_token_oc_proxy')
                    }
                }
            }
        }
    }
}