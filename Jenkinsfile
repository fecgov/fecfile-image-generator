pipeline{
  agent any
  stages{
    stage('Prepare Build'){
      steps{
        script{
          hash = sh(returnStdout: true, script: 'git rev-parse HEAD').trim()
          VERSION = hash.take(7)
          currentBuild.displayName = "#${BUILD_ID}-${VERSION}"
          sh("eval \$(aws ecr --region us-east-1 get-login --no-include-email)")
        }
      }
    }
  
    stage('Build ImageGenerator'){
      steps{
        script{
          def imageGenerator = docker.build("fecfile-imagegenerator:${VERSION}", ".")
          docker.withRegistry('https://813218302951.dkr.ecr.us-east-1.amazonaws.com/fecfile-imagegenerator'){
            imageGenerator.push()
          }
        }
      }
    }
    stage('Deploy Dev'){
      when { branch 'develop' }
      steps {
        deployImage16("${VERSION}", "dev")
        code_quality("${BUILD_ID}", "${VERSION}")
      }
    }
    stage('Deploy QA'){
      when { branch 'release' }
      steps {
        deployImage16("${VERSION}", "qa")
      }
    }
    stage('Deploy UAT'){
      when { branch 'master' }
      steps {
        deployImage16("${VERSION}", "uat")
      }
    }
  }
  post{
    success {
      slackSend color: 'good', message: env.BRANCH_NAME + ": Deployed ${VERSION} to k8s dev-efile-api.efdev.fec.gov/printpdf/"
    }
    failure {
      slackSend color: 'danger', message: env.BRANCH_NAME + ": deployment of fecfile-imagegenerator versoin: ${VERSION} failed!"
    }
  }
}
def deployImage(String version, String toEnv) {
   sh """ 
     kubectl \
       --context=arn:aws:eks:us-east-1:813218302951:cluster/fecfile4 \
       --namespace=${toEnv} \
       set image deployment/fecfile-imagegenerator \
       fecfile-imagegenerator=813218302951.dkr.ecr.us-east-1.amazonaws.com/fecfile-imagegenerator:${version}
   """
}

def deployImage16(String version, String toEnv) {
   sh """ 
     kubectl16 \
       --context=arn:aws:eks:us-east-1:813218302951:cluster/fecnxg-dev1 \
       --namespace=${toEnv} \
       set image deployment/fecfile-imagegenerator \
       fecfile-imagegenerator=813218302951.dkr.ecr.us-east-1.amazonaws.com/fecfile-imagegenerator:${version}
   """
}

def code_quality(String id, String hash) {
    sh(""" sh successful_test.sh "${id}" ${hash} """)
    junit '**/reports/*.xml'
}
