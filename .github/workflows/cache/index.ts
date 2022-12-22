
module.exports = async ({context}) => {
  console.log('Hello, world!');
  console.log('The event name is: ' + context.eventName);
  console.log('The ref is: ' + context.ref);
  console.log('The sha is: ' + context.sha);
  console.log('The workflow is: ' + context.workflow);
  console.log('The action is: ' + context.action);
  console.log('The actor is: ' + context.actor);
  console.log('The job name is: ' + context.job);
  console.log('The run number is: ' + context.runNumber);
  console.log('The run id is: ' + context.runId);
  console.log('The node index is: ' + context.nodeIndex);
  console.log('The node id is: ' + context.nodeId);
  console.log('The payload is: ' + JSON.stringify(context.payload));
};
