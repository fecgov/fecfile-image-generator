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
        sh("kubectl --context=arn:aws:eks:us-east-1:813218302951:cluster/fecfile --namespace=dev set image deployment/fecfile-imagegenerator fecfile-imagegenerator=813218302951.dkr.ecr.us-east-1.amazonaws.com/fecfile-imagegenerator:${VERSION}")
      }
    }
    stage('Deploy QA'){
      when { branch 'release' }
      steps {
        sh("kubectl --context=arn:aws:eks:us-east-1:813218302951:cluster/fecfile --namespace=qa set image deployment/fecfile-imagegenerator fecfile-imagegenerator=813218302951.dkr.ecr.us-east-1.amazonaws.com/fecfile-imagegenerator:${VERSION}")
      }
    }
    stage('Deploy UAT'){
      when { branch 'master' }
      steps {
        sh("kubectl --context=arn:aws:eks:us-east-1:813218302951:cluster/fecfile --namespace=uat set image deployment/fecfile-imagegenerator fecfile-imagegenerator=813218302951.dkr.ecr.us-east-1.amazonaws.com/fecfile-imagegenerator:${VERSION}")
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
