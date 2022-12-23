
module.exports = async ({context, github}) => {
  console.log('The payload is: ' + JSON.stringify(context.payload));
  console.log(github)
};
