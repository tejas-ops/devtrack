// Jenkinsfile — Declarative Pipeline for DevTrack CI/CD
//
// INTERVIEW MUST-KNOWS:
//   Declarative vs Scripted:
//     Declarative  = structured, uses pipeline{} block, easier to read, most common
//     Scripted     = uses node{} block, full Groovy, more flexible but harder to maintain
//
//   This pipeline runs whenever someone pushes to main or opens a PR.
//   Stages run sequentially. 'parallel' blocks run stages concurrently.
//
// WHY Groovy?
//   Jenkins is written in Java. Jenkinsfile is Groovy (JVM language).
//   String interpolation:  "${VARIABLE}"  (use double quotes!)
//   Closures:  { -> ... } or just { ... }

pipeline {

    // Which agent (Jenkins worker node) runs this pipeline
    agent {
        // Run inside a Docker container — clean environment every time
        docker {
            image 'python:3.11-slim'
            // This means: spin up a python:3.11-slim container, run pipeline inside it
            args  '--user root'  // need root to install packages
        }
    }

    // ── Pipeline parameters — appear as dropdowns in Jenkins UI ──
    parameters {
        choice(
            name:        'DEPLOY_ENV',
            choices:     ['dev', 'staging', 'prod'],
            description: 'Target deployment environment'
        )
        booleanParam(
            name:         'SKIP_TESTS',
            defaultValue: false,
            description:  'Skip test stage (emergency hotfix only!)'
        )
        string(
            name:         'IMAGE_TAG',
            defaultValue: '',
            description:  'Docker image tag override (leave blank to use git SHA)'
        )
    }

    // ── Environment variables available to all stages ──
    environment {
        APP_NAME       = 'devtrack-api'
        REGISTRY       = 'myregistry.azurecr.io'
        IMAGE_TAG      = "${params.IMAGE_TAG ?: env.GIT_COMMIT[0..7]}"
        // GIT_COMMIT[0..7] = first 8 chars of git SHA = short SHA
        // ?: is the Groovy Elvis operator = "use left side if not null/empty"

        FULL_IMAGE     = "${REGISTRY}/${APP_NAME}:${IMAGE_TAG}"

        // withCredentials injects these as env vars securely (values are masked in logs)
        ACR_CREDENTIALS  = credentials('acr-service-principal')
        // ACR_CREDENTIALS_USR = username, ACR_CREDENTIALS_PSW = password (auto-set)

        KUBECONFIG_FILE  = credentials('aks-kubeconfig')
        // 'aks-kubeconfig' = a "Secret file" credential stored in Jenkins
    }

    // ── Pipeline options ──
    options {
        timeout(time: 30, unit: 'MINUTES')   // fail the pipeline if it runs > 30 mins
        disableConcurrentBuilds()             // only one build at a time per branch
        buildDiscarder(logRotator(numToKeepStr: '10'))  // keep last 10 builds
        timestamps()                          // add timestamps to every log line
    }

    stages {

        // ─── Stage 1: Checkout ───────────────────────────────────────────────
        stage('Checkout') {
            steps {
                // Jenkins checks out the code automatically when using a Jenkinsfile
                // But we print info here for debugging
                script {
                    echo "Branch:  ${env.BRANCH_NAME}"
                    echo "Commit:  ${env.GIT_COMMIT}"
                    echo "Image:   ${FULL_IMAGE}"
                }
                sh 'git log -1 --oneline'   // show the commit being built
            }
        }

        // ─── Stage 2: Install dependencies ──────────────────────────────────
        stage('Install') {
            steps {
                sh '''
                    pip install --no-cache-dir -r requirements.txt
                    pip install --no-cache-dir pylint
                '''
                // Using triple-quoted strings for multi-line shell commands
            }
        }

        // ─── Stage 3: Lint + Tests (run in parallel to save time) ───────────
        stage('Quality Gates') {
            when {
                // Skip this stage if SKIP_TESTS parameter is true
                expression { return !params.SKIP_TESTS }
            }
            parallel {
                // These two stages run AT THE SAME TIME
                stage('Lint') {
                    steps {
                        sh '''
                            pylint app/ --fail-under=7.0
                            # --fail-under=7.0: fail if code score < 7/10
                        '''
                    }
                }
                stage('Tests') {
                    steps {
                        sh '''
                            pytest tests/ \
                                --junitxml=test-results.xml \
                                --cov=app \
                                --cov-report=xml:coverage.xml \
                                --cov-fail-under=80
                            # --junitxml: output Jenkins can parse and display
                            # --cov-fail-under=80: fail if test coverage < 80%
                        '''
                    }
                    post {
                        always {
                            // Publish test results in Jenkins UI regardless of pass/fail
                            junit 'test-results.xml'
                            // Publish coverage report
                            cobertura coberturaReportFile: 'coverage.xml'
                        }
                    }
                }
            }
        }

        // ─── Stage 4: Build Docker image ────────────────────────────────────
        stage('Build Image') {
            steps {
                script {
                    // Use credentials to log in to Azure Container Registry
                    withCredentials([usernamePassword(
                        credentialsId: 'acr-service-principal',
                        usernameVariable: 'ACR_USER',
                        passwordVariable: 'ACR_PASS'
                    )]) {
                        sh """
                            echo "\$ACR_PASS" | docker login ${REGISTRY} \
                                --username "\$ACR_USER" --password-stdin
                            # --password-stdin: read password from stdin (not visible in logs!)

                            docker build \
                                --tag ${FULL_IMAGE} \
                                --tag ${REGISTRY}/${APP_NAME}:latest \
                                --build-arg BUILD_DATE=\$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
                                --build-arg GIT_COMMIT=${env.GIT_COMMIT} \
                                .
                        """
                    }
                }
            }
        }

        // ─── Stage 5: Security scan ──────────────────────────────────────────
        stage('Security Scan') {
            steps {
                sh """
                    # Trivy scans Docker images for known CVEs (vulnerabilities)
                    trivy image \
                        --exit-code 1 \
                        --severity HIGH,CRITICAL \
                        --no-progress \
                        ${FULL_IMAGE}
                    # --exit-code 1: fail the pipeline if HIGH/CRITICAL CVEs found
                """
            }
        }

        // ─── Stage 6: Push image ─────────────────────────────────────────────
        stage('Push Image') {
            steps {
                sh """
                    docker push ${FULL_IMAGE}
                    docker push ${REGISTRY}/${APP_NAME}:latest
                """
            }
        }

        // ─── Stage 7: Deploy ─────────────────────────────────────────────────
        stage('Deploy') {
            when {
                // Only deploy automatically from main/master branch
                anyOf {
                    branch 'main'
                    branch 'master'
                }
            }
            steps {
                script {
                    def environment = params.DEPLOY_ENV

                    // Human approval gate for production deployments
                    if (environment == 'prod') {
                        input(
                            message: "Deploy ${IMAGE_TAG} to PRODUCTION?",
                            ok:      "Yes, deploy!",
                            // submitter: 'tech-leads'  // only these users can approve
                        )
                    }

                    withCredentials([file(credentialsId: 'aks-kubeconfig', variable: 'KUBECONFIG')]) {
                        sh """
                            export KUBECONFIG=\$KUBECONFIG

                            # Update the image tag in the Deployment
                            kubectl set image \
                                deployment/${APP_NAME} \
                                ${APP_NAME}=${FULL_IMAGE} \
                                --namespace=devtrack

                            # Wait for rollout to complete (max 5 mins)
                            kubectl rollout status \
                                deployment/${APP_NAME} \
                                --namespace=devtrack \
                                --timeout=300s
                        """
                    }

                    // Update deployment status in DevTrack itself (dog-fooding!)
                    sh """
                        curl -s -X POST http://devtrack-api.devtrack.svc.cluster.local/deployments/ \\
                            -H 'Content-Type: application/json' \\
                            -d '{
                                "app_name":    "${APP_NAME}",
                                "version":     "${IMAGE_TAG}",
                                "environment": "${environment}",
                                "deployed_by": "jenkins",
                                "status":      "success"
                            }'
                    """
                }
            }
        }
    }

    // ── Post-build actions (run after ALL stages) ──
    post {
        success {
            echo "Pipeline SUCCESS — ${APP_NAME}:${IMAGE_TAG} deployed to ${params.DEPLOY_ENV}"
            // slackSend channel: '#deployments', message: "✅ Deployed ${FULL_IMAGE}"
        }
        failure {
            echo "Pipeline FAILED — check logs above"
            // slackSend channel: '#deployments', color: 'danger', message: "❌ Failed: ${FULL_IMAGE}"
            // emailext to: 'team@example.com', subject: "Build Failed: ${JOB_NAME}", body: "..."
        }
        always {
            // Clean up docker images on the agent to save disk space
            sh "docker rmi ${FULL_IMAGE} || true"
            // || true: don't fail the pipeline if the image isn't there
        }
        cleanup {
            cleanWs()   // delete workspace files after build
        }
    }
}
