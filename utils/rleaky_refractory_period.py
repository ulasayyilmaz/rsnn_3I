import torch
import torch.nn as nn

# from torch import functional as F
from snntorch._neurons.neurons import LIF

class RLeaky_refractory(LIF):
    """
    First-order recurrent leaky integrate-and-fire neuron model.
    Input is assumed to be a current injection appended to the voltage
    spike output.
    Membrane potential decays exponentially with rate beta.
    For :math:`U[T] > U_{\\rm thr} ⇒ S[T+1] = 1`.

    If `reset_mechanism = "subtract"`, then :math:`U[t+1]` will have
    `threshold` subtracted from it whenever the neuron emits a spike:

    .. math::

            U[t+1] = βU[t] + I_{\\rm in}[t+1] + V(S_{\\rm out}[t]) -
            RU_{\\rm thr}

    Where :math:`V(\\cdot)` acts either as a linear layer, a convolutional
    operator, or elementwise product on :math:`S_{\\rm out}`.

    * If `all_to_all = "True"` and `linear_features` is specified, then \
        :math:`V(\\cdot)` acts as a recurrent linear layer of the \
        same size as :math:`S_{\\rm out}`.
    * If `all_to_all = "True"` and `conv2d_channels` and `kernel_size` are \
        specified, then :math:`V(\\cdot)` acts as a recurrent convlutional \
        layer \
        with padding to ensure the output matches the size of the input.
    * If `all_to_all = "False"`, then :math:`V(\\cdot)` acts as an \
        elementwise multiplier with :math:`V`.

    * If `reset_mechanism = "zero"`, then :math:`U[t+1]` will be set to `0` \
        whenever the neuron emits a spike:

    .. math::
            U[t+1] = βU[t] + I_{\\rm in}[t+1] +  V(S_{\\rm out}[t]) -
            R(βU[t] + I_{\\rm in}[t+1] +  V(S_{\\rm out}[t]))

    * :math:`I_{\\rm in}` - Input current
    * :math:`U` - Membrane potential
    * :math:`U_{\\rm thr}` - Membrane threshold
    * :math:`S_{\\rm out}` - Output spike
    * :math:`R` - Reset mechanism: if active, :math:`R = 1`, otherwise \
        :math:`R = 0`
    * :math:`β` - Membrane potential decay rate
    * :math:`V` - Explicit recurrent weight when `all_to_all=False`

    Example::

        import torch
        import torch.nn as nn
        import snntorch as snn

        beta = 0.5 # decay rate
        V1 = 0.5 # shared recurrent connection
        V2 = torch.rand(num_outputs) # unshared recurrent connections

        # Define Network
        class Net(nn.Module):
            def __init__(self):
                super().__init__()

                # initialize layers
                self.fc1 = nn.Linear(num_inputs, num_hidden)

                # Default RLeaky Layer where recurrent connections
                # are initialized using PyTorch defaults in nn.Linear.
                self.lif1 = snn.RLeaky(beta=beta,
                            linear_features=num_hidden)

                self.fc2 = nn.Linear(num_hidden, num_outputs)

                # each neuron has a single connection back to itself
                # where the output spike is scaled by V.
                # For `all_to_all = False`, V can be shared between
                # neurons (e.g., V1) or unique / unshared between
                # neurons (e.g., V2).
                # V is learnable by default.
                self.lif2 = snn.RLeaky(beta=beta, all_to_all=False, V=V1)

            def forward(self, x):
                # Initialize hidden states at t=0
                spk1, mem1 = self.lif1.init_rleaky()
                spk2, mem2 = self.lif2.init_rleaky()

                # Record output layer spikes and membrane
                spk2_rec = []
                mem2_rec = []

                # time-loop
                for step in range(num_steps):
                    cur1 = self.fc1(x)
                    spk1, mem1 = self.lif1(cur1, spk1, mem1)
                    cur2 = self.fc2(spk1)
                    spk2, mem2 = self.lif2(cur2, spk2, mem2)

                    spk2_rec.append(spk2)
                    mem2_rec.append(mem2)

                # convert lists to tensors
                spk2_rec = torch.stack(spk2_rec)
                mem2_rec = torch.stack(mem2_rec)

                return spk2_rec, mem2_rec

    :param beta: membrane potential decay rate. Clipped between 0 and 1
        during the forward-pass. May be a single-valued tensor (i.e., equal
        decay rate for all neurons in a layer), or multi-valued
        (one weight per neuron).
    :type beta: float or torch.tensor

    :param V: Recurrent weights to scale output spikes, only used when
        `all_to_all=False`. Defaults to 1.
    :type V: float or torch.tensor

    :param all_to_all: Enables output spikes to be connected in dense or
        convolutional recurrent structures instead of 1-to-1 connections.
        Defaults to True.
    :type all_to_all: bool, optional

    :param linear_features: Size of each output sample. Must be specified
        if `all_to_all=True` and the input data is 1D. Defaults to None
    :type linear_features: int, optional

    :param conv2d_channels: Number of channels in each output sample. Must
        be specified if `all_to_all=True` and the input data is 3D.
        Defaults to None
    :type conv2d_channels: int, optional

    :param kernel_size:  Size of the convolving kernel. Must be
        specified if `all_to_all=True` and the input data is 3D.
        Defaults to None
    :type kernel_size: int or tuple

    :param threshold: Threshold for :math:`mem` to reach in order to
        generate a spike `S=1`. Defaults to 1 :type threshold: float,
        optional

    :param spike_grad: Surrogate gradient for the term dS/dU. Defaults
        to None (corresponds to ATan surrogate gradient. See
        `snntorch.surrogate` for more options)
    :type spike_grad: surrogate gradient function from snntorch.surrogate,
        optional

    :param surrogate_disable: Disables surrogate gradients regardless of
        `spike_grad` argument. Useful for ONNX compatibility. Defaults
        to False
    :type surrogate_disable: bool, Optional

    :param init_hidden: Instantiates state variables as instance variables.
        Defaults to False :type init_hidden: bool, optional

    :param inhibition: If `True`, suppresses all spiking other than the
        neuron with the highest state. Defaults to False :type inhibition:
        bool, optional

    :param learn_beta: Option to enable learnable beta. Defaults to False
    :type learn_beta: bool, optional

    :param learn_recurrent: Option to enable learnable recurrent weights.
        Defaults to True
    :type learn_recurrent: bool, optional

    :param learn_threshold: Option to enable learnable threshold.
        Defaults to False
    :type learn_threshold: bool, optional

    :param reset_mechanism: Defines the reset mechanism applied to
        :math:`mem` each time the threshold is met.
        Reset-by-subtraction: "subtract", reset-to-zero: "zero",
        none: "none". Defaults to "subtract"
    :type reset_mechanism: str, optional

    :param state_quant: If specified, hidden state :math:`mem` is
        quantized to a valid state for the forward pass. Defaults to False
    :type state_quant: quantization function from snntorch.quant, optional

    :param output: If `True` as well as `init_hidden=True`, states are
        returned when neuron is called. Defaults to False :type output:
        bool, optional




    Inputs: \\input_, spk_0, mem_0
        - **input_** of shape `(batch, input_size)`: tensor containing
        input
          features
        - **spk_0** of shape `(batch, input_size)`: tensor containing
        output
          spike features
        - **mem_0** of shape `(batch, input_size)`: tensor containing the
          initial membrane potential for each element in the batch.

    Outputs: spk_1, mem_1
        - **spk_1** of shape `(batch, input_size)`: tensor containing the
        output
          spikes.
        - **mem_1** of shape `(batch, input_size)`: tensor containing
        the next
          membrane potential for each element in the batch

    Learnable Parameters:
        - **RLeaky.beta** (torch.Tensor) - optional learnable weights
        must be
          manually passed in, of shape `1` or (input_size).
        - **RLeaky.recurrent.weight** (torch.Tensor) - optional learnable
          weights are automatically generated if `all_to_all=True`.
          `RLeaky.recurrent` stores a `nn.Linear` or `nn.Conv2d` layer
          depending on input arguments provided.
        - **RLeaky.V** (torch.Tensor) - optional learnable weights must be
          manually passed in, of shape `1` or (input_size). It is only used
          where `all_to_all=False` for 1-to-1 recurrent connections.
        - **RLeaky.threshold** (torch.Tensor) - optional learnable
            thresholds must be manually passed in, of shape `1` or``
            (input_size).

    """

    def __init__(
        self,
        beta,
        V=1.0,
        all_to_all=True,
        linear_features=None,
        conv2d_channels=None,
        kernel_size=None,
        threshold=1.0,
        spike_grad=None,
        surrogate_disable=False,
        init_hidden=False,
        inhibition=False,
        learn_beta=False,
        learn_threshold=False,
        learn_recurrent=True,  # changed learn_V
        reset_mechanism="zero",
        state_quant=False,
        output=False,
        reset_delay=True,
        refractory_period=4,
    ):
        super().__init__(
            beta,
            threshold,
            spike_grad,
            surrogate_disable,
            init_hidden,
            inhibition,
            learn_beta,
            learn_threshold,
            reset_mechanism,
            state_quant,
            output,
        )

        self.all_to_all = all_to_all
        self.learn_recurrent = learn_recurrent

        # linear params
        self.linear_features = linear_features

        # Conv2d params
        self.kernel_size = kernel_size
        self.conv2d_channels = conv2d_channels

        # catch cases
        self._rleaky_init_cases()

        # initialize recurrent connections
        if self.all_to_all:  # init all-all connections
            self._init_recurrent_net()
        else:  # initialize 1-1 connections
            self._V_register_buffer(V, learn_recurrent)
            self._init_recurrent_one_to_one()

        if not learn_recurrent:
            self._disable_recurrent_grad()

        self._init_mem()

        if self.reset_mechanism_val == 0:  # reset by subtraction
            self.state_function = self._base_sub
        elif self.reset_mechanism_val == 1:  # reset to zero
            self.state_function = self._base_zero
        elif self.reset_mechanism_val == 2:  # no reset, pure integration
            self.state_function = self._base_int

        self.reset_delay = reset_delay
        self.refractory_period = refractory_period

    def _init_mem(self):
        spk = torch.zeros(0)
        mem = torch.zeros(0)
        refractory_counter = torch.zeros(0)

        self.register_buffer("spk", spk, False)
        self.register_buffer("mem", mem, False)
        self.register_buffer("refractory_counter", refractory_counter, False)

    def reset_mem(self):
        self.spk = torch.zeros_like(self.spk, device=self.spk.device)
        self.mem = torch.zeros_like(self.mem, device=self.mem.device)
        self.refractory_counter = torch.zeros_like(self.refractory_counter, device=self.refractory_counter.device)
        return self.spk, self.mem

    def init_rleaky(self):
        """Deprecated, use :class:`RLeaky.reset_mem` instead"""
        return self.reset_mem()

    def forward(self, input_, spk=None, mem=None, refractory_counter=None):

        if not spk == None:
            self.spk = spk

        if not mem == None:
            self.mem = mem

        if not refractory_counter == None:
            self.refractory_counter = refractory_counter

        if self.init_hidden and (not mem == None or not spk == None or not refractory_counter == None):
            raise TypeError(
                "When `init_hidden=True`," "RLeaky expects 1 input argument."
            )

        if not self.spk.shape == input_.shape:
            self.spk = torch.zeros_like(input_, device=self.spk.device)

        if not self.mem.shape == input_.shape:
            self.mem = torch.zeros_like(input_, device=self.mem.device)

        if not self.refractory_counter.shape == input_.shape:
            self.refractory_counter = torch.zeros_like(input_, device=self.refractory_counter.device)

        # With each forward, decrement the counter
        self.refractory_counter = torch.clamp(self.refractory_counter - 1, min=0)

        # TO-DO: alternatively, we could do torch.exp(-1 /
        # self.beta.clamp_min(0)), giving actual time constants instead of
        # values in [0, 1] as initial beta beta = self.beta.clamp(0, 1)

        self.reset = self.mem_reset(self.mem)
        self.mem = self.state_function(input_)

        # Set a spike on when refractory period is 0
        refractory_mask = (self.refractory_counter == 0)
        self.spk = self.fire(self.mem) * refractory_mask

        # Update the refractory counter back to 5 where spikes occurred
        self.refractory_counter[self.spk > 0] = self.refractory_period

        if self.state_quant:
            self.mem = self.state_quant(self.mem)

        if self.inhibition:
            self.spk = self.fire_inhibition(self.mem.size(0), self.mem) * refractory_mask
        else:
            self.spk = self.fire(self.mem) * refractory_mask

        if not self.reset_delay:
            do_reset = (
                self.spk / self.graded_spikes_factor - self.reset
            )  # avoid double reset
            if self.reset_mechanism_val == 0:  # reset by subtraction
                self.mem = self.mem - do_reset * self.threshold
            elif self.reset_mechanism_val == 1:  # reset to zero
                self.mem = self.mem - do_reset * self.mem

        if self.output:
            return self.spk, self.mem
        elif self.init_hidden:
            return self.spk
        else:
            return self.spk, self.mem

    def _init_recurrent_net(self):
        if self.all_to_all:
            if self.linear_features:
                self._init_recurrent_linear()
            elif self.kernel_size is not None:
                self._init_recurrent_conv2d()
        else:
            self._init_recurrent_one_to_one()

    def _init_recurrent_linear(self):
        self.recurrent = nn.Linear(self.linear_features, self.linear_features)

    def _init_recurrent_conv2d(self):
        self._init_padding()
        self.recurrent = nn.Conv2d(
            in_channels=self.conv2d_channels,
            out_channels=self.conv2d_channels,
            kernel_size=self.kernel_size,
            padding=self.padding,
        )

    def _init_padding(self):
        if type(self.kernel_size) is int:
            self.padding = self.kernel_size // 2, self.kernel_size // 2
        else:
            self.padding = self.kernel_size[0] // 2, self.kernel_size[1] // 2

    def _init_recurrent_one_to_one(self):
        self.recurrent = RecurrentOneToOne(self.V)

    def _disable_recurrent_grad(self):
        for param in self.recurrent.parameters():
            param.requires_grad = False

    def _base_state_function(self, input_):
        base_fn = (
            self.beta.clamp(0, 1) * self.mem
            + input_
            + self.recurrent(self.spk)
        )
        return base_fn

    def _base_sub(self, input_):
        return self._base_state_function(input_) - self.reset * self.threshold

    def _base_zero(self, input_):
        return self._base_state_function(
            input_
        ) - self.reset * self._base_state_function(input_)

    def _base_int(self, input_):
        return self._base_state_function(input_)

    def _rleaky_init_cases(self):
        all_to_all_bool = bool(self.all_to_all)
        linear_features_bool = self.linear_features
        conv2d_channels_bool = bool(self.conv2d_channels)
        kernel_size_bool = bool(self.kernel_size)

        if all_to_all_bool:
            if not (linear_features_bool):
                if not (conv2d_channels_bool or kernel_size_bool):
                    raise TypeError(
                        "When `all_to_all=True`, RLeaky requires either"
                        "`linear_features` or (`conv2d_channels` and "
                        "`kernel_size`) to be specified. The "
                        "shape should match the shape of the output spike of "
                        "the layer."
                    )
                elif conv2d_channels_bool ^ kernel_size_bool:
                    raise TypeError(
                        "`conv2d_channels` and `kernel_size` must both be"
                        "specified. The shape of `conv2d_channels` should "
                        "match the shape of the output"
                        "spikes."
                    )
            elif (linear_features_bool and kernel_size_bool) or (
                linear_features_bool and conv2d_channels_bool
            ):
                raise TypeError(
                    "`linear_features` cannot be specified at the same time as"
                    "`conv2d_channels` or `kernel_size`. A linear layer and "
                    "conv2d layer cannot both"
                    "be specified at the same time."
                )
        else:
            if (
                linear_features_bool
                or conv2d_channels_bool
                or kernel_size_bool
            ):
                raise TypeError(
                    "When `all_to_all`=False, none of `linear_features`,"
                    "`conv2d_channels`, or `kernel_size` should be specified. "
                    "The weight `V` is used"
                    "instead."
                )
    
    @classmethod
    def detach_hidden(cls):
        """Returns the hidden states, detached from the current graph.
        Intended
        for use in truncated backpropagation through time where hidden state
        variables
        are instance variables."""

        for layer in range(len(cls.instances)):
            if isinstance(cls.instances[layer], RLeaky):
                cls.instances[layer].mem.detach_()
                cls.instances[layer].spk.detach_()



    @classmethod
    def detach_hidden(cls):
        """Returns the hidden states, detached from the current graph.
        Intended
        for use in truncated backpropagation through time where hidden state
        variables
        are instance variables."""

        for layer in range(len(cls.instances)):
            if isinstance(cls.instances[layer], RLeaky):
                cls.instances[layer].mem.detach_()
                cls.instances[layer].spk.detach_()