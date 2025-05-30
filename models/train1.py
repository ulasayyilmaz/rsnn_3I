import torch
from utils.helper1 import count_spikes


#function to train and save the variables to npz files!
def train_model16(args):
    job, model, optimizer, dataloader,criterion, taskid, ineuron, num_epochs, num_timesteps= args
    model.train()
    for epoch in range(num_epochs):
        epoch_loss = 0

        for i, (inputs, targets) in enumerate(dataloader):
            inputs, targets = inputs, targets

            optimizer.zero_grad()

            outputs = torch.empty(0, dtype=torch.float32, requires_grad=True)
            spikes = torch.empty(0, dtype=torch.float32)  # Initialize spike storage

            for input, _ in zip(inputs, targets):
                output, spike = model(input)
                spike = spike.T

                # outputs of dimension [25,300]
                outputs = torch.cat((outputs, output.view(1, -1)))
                # spikes of dimension [25,200,300]
                spikes = torch.cat((spikes, spike.unsqueeze(0)))
                    
            loss = (outputs, targets)

            print("loss:", loss)
            loss.backward()
            optimizer.step()
            
            # try
            model.positive_negative_weights()
            
            epoch_loss += loss.item()

            if epoch % 10 == 0:
                torch.save({
                    "task_loss":criterion.task_loss.item(),
                    "spikes":spikes,
                    "input_weights":model.l1.weight.data,
                    "rec_weights":model.rlif1.recurrent.weight.data,
                    "output_weights":model.l2.weight.data,
                    "inputs":inputs,
                    "outputs":outputs,
                    "targets":targets},
                    f'data/output/task{taskid}_i{ineuron}_job{job}_epoch{epoch}_batch{i}.pth')


# train function that integrates firing rate, criticality and synchrony
# may need updating...
# def train_model(args):
#     model, optimizer, dataloader,step_dataloader, criterion, criterium_idx, num_epochs, num_timesteps= args
#     model.train()
#     for epoch in range(num_epochs):
#         epoch_loss = 0

#         for i, (inputs, targets) in enumerate(dataloader):
#             inputs, targets = inputs, targets

#             optimizer.zero_grad()

#             outputs = torch.empty(0, dtype=torch.float32, requires_grad=True)
#             # firing_rate_per_batch = torch.empty(0, dtype=torch.float32, requires_grad=True)
#             # criticality_per_batch = torch.empty(0, dtype=torch.float32, requires_grad=True)
#             # synchrony_per_batch = torch.empty(0, dtype=torch.float32, requires_grad=True)

#             for input, target in zip(inputs, targets):
#                 output, spikes = model(input)
#                 spikes = spikes.T
#                 outputs = torch.cat((outputs, output.view(1, -1)))

# #                 firing_rate = count_spikes(spikes) / 30000
# #                 firing_rate_per_batch = torch.cat((firing_rate_per_batch, firing_rate))

# #                 criticality = simple_branching_param(1, spikes).reshape([1])
# #                 criticality_per_batch = torch.cat((criticality_per_batch, criticality))

# #                 synchrony_fano_factor = fano_factor(num_timesteps, spikes).reshape([1])
# #                 synchrony_per_batch = torch.cat((synchrony_per_batch, synchrony_fano_factor))

#             # loss = criterion(outputs, targets, criticality_per_batch, firing_rate_per_batch, synchrony_per_batch)
            
#             loss = criterion(outputs, targets)
#             print("loss:", loss)
#             loss.backward()
#             optimizer.step()
            
#             #call positive_negative_weights
#             model.positive_negative_weights()

#             epoch_loss += loss.item()

#             if epoch % 5 == 0:
#                 np.savez(f'dataMP/level{step_dataloader}_loss{criterium_idx}_epoch{epoch}_batch{i}.npz',
#                          task_loss=criterion.task_loss.item(),
#                          spikes=spikes.detach().numpy(),
#                          input_weights=model.l1.weight.data.detach().numpy(),
#                          rec_weights=model.rlif1.recurrent.weight.data.detach().numpy(),
#                          output_weights=model.l2.weight.data.detach().numpy(),
#                          inputs=inputs.detach().numpy(),
#                          outputs=outputs.detach().numpy(),
#                          targets=targets.detach().numpy())

                
# function that tries to eliminate the clock_like input. 5 distinct dataloaders. First 200 epochs, trains on amplitude,
# period, and clock-like input. 200-400th epochs, clocklike input vector vlaues are squished closer to zero by 1/5. 
# assume if clock_like vector was originally [-10, -5, -3, -1, 0, 1, 3, 5, 10], then values become: [-8, -4, -2.2, -4/5, 0 ...]
# always squished by 1/5 of the original magnitudes. by 1000th epoch, clocklike input becomes
# [0,0,0,0,0...], the model doesn't learn..
# #model8 traines on different dataloaders each 200th epoch
# def train_model8(args):
#     model, optimizer, dataloader_list,step_dataloader, criterion, criterium_idx, num_epochs, num_timesteps= args
#     model.train()
#     for epoch in range(num_epochs):
#         epoch_loss = 0

#         if epoch < 200:
#             dataloader = dataloader_list[0]
#             print(1)
#         elif epoch < 400:
#             dataloader = dataloader_list[1]
#             print(2)
#         elif epoch < 600:
#             dataloader = dataloader_list[2]
#             print(3)
#         elif epoch < 800:
#             dataloader = dataloader_list[3]
#             print(4)
#         elif epoch < 1000:
#             dataloader = dataloader_list[4]
#             print(5)
            
#         for i, (inputs, targets) in enumerate(dataloader):
#             inputs, targets = inputs, targets

#             optimizer.zero_grad()

#             outputs = torch.empty(0, dtype=torch.float32, requires_grad=True)
#             # firing_rate_per_batch = torch.empty(0, dtype=torch.float32, requires_grad=True)
#             # criticality_per_batch = torch.empty(0, dtype=torch.float32, requires_grad=True)
#             # synchrony_per_batch = torch.empty(0, dtype=torch.float32, requires_grad=True)

#             for input, target in zip(inputs, targets):
#                 output, spikes = model(input)
#                 spikes = spikes.T
#                 outputs = torch.cat((outputs, output.view(1, -1)))

# #                 firing_rate = count_spikes(spikes) / 30000
# #                 firing_rate_per_batch = torch.cat((firing_rate_per_batch, firing_rate))

# #                 criticality = simple_branching_param(1, spikes).reshape([1])
# #                 criticality_per_batch = torch.cat((criticality_per_batch, criticality))

# #                 synchrony_fano_factor = fano_factor(num_timesteps, spikes).reshape([1])
# #                 synchrony_per_batch = torch.cat((synchrony_per_batch, synchrony_fano_factor))

#             # loss = criterion(outputs, targets, criticality_per_batch, firing_rate_per_batch, synchrony_per_batch)
            
#             loss = criterion(outputs, targets)
#             print("loss:", loss)
#             loss.backward()
#             optimizer.step()

#             epoch_loss += loss.item()

#             if epoch % 5 == 0:
#                 np.savez(f'dataMP/level{step_dataloader}_loss{criterium_idx}_epoch{epoch}_batch{i}.npz',
#                          task_loss=criterion.task_loss.item(),
#                          spikes=spikes.detach().numpy(),
#                          input_weights=model.l1.weight.data.detach().numpy(),
#                          rec_weights=model.rlif1.recurrent.weight.data.detach().numpy(),
#                          output_weights=model.l2.weight.data.detach().numpy(),
#                          inputs=inputs.detach().numpy(),
#                          outputs=outputs.detach().numpy(),
#                          targets=targets.detach().numpy())
