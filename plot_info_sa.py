# Python imports.
import os, sys, random, math
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as pyplot
import numpy as np

# Other imports.
from simple_rl.abstraction.AbstractionWrapperClass import AbstractionWrapper
from simple_rl.abstraction.state_abs.ProbStateAbstractionClass import ProbStateAbstraction, convert_prob_sa_to_sa
from simple_rl.tasks import FourRoomMDP, GridWorldMDP
from simple_rl.planning import ValueIteration
from simple_rl.agents import FixedPolicyAgent
from simple_rl.run_experiments import evaluate_agent
from simple_rl.utils import chart_utils
from rlit_utils import write_datum_to_file, end_of_instance

# -------------------
# -- DIBS Plotting --
# -------------------

def make_info_sa_val_and_size_plots(mdp, demo_policy_lambda, beta_range, results_dir="info_sa_results", instances=3, include_stoch=False, is_agent_in_control=False):
    '''
    Args:
        mdp (simple_rl.MDP)
        demo_policy_lambda (lambda : simple_rl.State --> str)
        beta_range (list)
        results_dir (str)
        instances (int)
        include_stoch (bool): If True, also runs IB.
        is_agent_in_control (bool): If True, runs the agent_in_control.py variant of DIB-SA.

    Summary:
        Main plotting function for info_sa experiments.
    '''
    # Clear old results.
    all_policies = ["demo_val", "dibs_val", "dibs_states", "etad_states"]
    if include_stoch:
        all_policies += ["ib_val", "ib_states"]
    for policy in all_policies:
        if os.path.exists(os.path.join(results_dir, str(policy)) + ".csv"):
            os.remove(os.path.join(results_dir, str(policy)) + ".csv")

    # Set relevant params.
    param_dict = {"mdp":mdp, "iters":500, "convergence_threshold":0.0001, "demo_policy_lambda":demo_policy_lambda, "is_agent_in_control": is_agent_in_control}

    # Record vallue of demo policy and size of ground state space.
    demo_agent = FixedPolicyAgent(demo_policy_lambda)
    demo_val = evaluate_agent(demo_agent, mdp, instances=100)
    vi = ValueIteration(mdp)
    num_ground_states = vi.get_num_states()
    for beta in beta_range:
        write_datum_to_file(file_name="demo_val", datum=demo_val, extra_dir=results_dir)
        write_datum_to_file(file_name="ground_states", datum=num_ground_states, extra_dir=results_dir)

    # Run core algorithm for DIB and IB.
    for instance in range(instances):
        print "\nInstance", instance + 1, "of", str(instances) + "."
        random.jumpahead(1)

        # For each beta.
        for beta in beta_range:

            # Run DIB.
            dibs_val, dibs_states = _info_sa_val_and_size_plot_wrapper(beta=beta, param_dict=dict(param_dict.items() + {"is_deterministic_ib":True,"use_crisp_policy":False}.items()))
            write_datum_to_file(file_name="dibs_val", datum=dibs_val, extra_dir=results_dir)
            write_datum_to_file(file_name="dibs_states", datum=dibs_states, extra_dir=results_dir)

            if include_stoch:
                ib_val, ib_states = _info_sa_val_and_size_plot_wrapper(beta=beta, param_dict=dict(param_dict.items() + {"is_deterministic_ib":False,"use_crisp_policy":False}.items()))
                write_datum_to_file(file_name="ib_val", datum=ib_val, extra_dir=results_dir)
                write_datum_to_file(file_name="ib_states", datum=ib_states, extra_dir=results_dir)

        # End instances.        
        end_of_instance("dibs_val", extra_dir=results_dir)
        end_of_instance("dibs_states", extra_dir=results_dir)
        if include_stoch:
            end_of_instance("ib_val", extra_dir=results_dir)
            end_of_instance("ib_states", extra_dir=results_dir)
    
    beta_range_file = file(os.path.join(results_dir, "beta_range.csv"), "w")
    for beta in beta_range:
        beta_range_file.write(str(beta))
        beta_range_file.write(",")

    beta_range_file.close()

    make_beta_val_plot([p for p in all_policies if "val" in p], results_dir, is_agent_in_control=is_agent_in_control)

def make_beta_val_plot(all_policies, results_dir, is_agent_in_control=False):
    '''
    Args:
        all_policies (list)
        results_dir (str)
    '''

    beta_range_file = file(os.path.join(results_dir, "beta_range.csv"), "r")
    beta_range = [float(beta) for beta in beta_range_file.read().split(",") if beta != ""]

    print beta_range

    # Set title and axes.
    chart_utils.CUSTOM_TITLE = "DIBS: Value vs. $\\beta$"
    if is_agent_in_control:
        chart_utils.CUSTOM_TITLE = "AC-" + chart_utils.CUSTOM_TITLE
    chart_utils.X_AXIS_LABEL = "$\\beta$"
    chart_utils.Y_AXIS_LABEL = "$V^{\\pi}$"
    chart_utils.X_AXIS_START_VAL = beta_range[0]
    chart_utils.X_AXIS_INCREMENT = beta_range[1] - beta_range[0]
    chart_utils.Y_AXIS_END_VAL = None

    # Val Plot.
    chart_utils.make_plots(experiment_dir=results_dir, experiment_agents=all_policies, plot_file_name="results_new3", cumulative=False, episodic=False, track_disc_reward=False)



# -----------------------
# -- PlotFunc Wrappers --
# -----------------------

def _info_sa_val_and_size_plot_wrapper(beta, param_dict):
    '''
    Args:
        beta (float): stands for $beta$ in the info_sa algorithm.
        param_dict (dict): contains relevant parameters for plotting.

    Returns:
        (tuple):
            (int) The value achieved by $pi_phi^*$ in the MDP.
            (int) The number of abstract states

    Notes:
        This serves as a wrapper to cooperate with PlotFunc.
    '''

    # Grab params.
    mdp = param_dict["mdp"]
    demo_policy_lambda = param_dict["demo_policy_lambda"]
    iters = param_dict["iters"]
    convergence_threshold = param_dict["convergence_threshold"]
    is_deterministic_ib = param_dict["is_deterministic_ib"]
    use_crisp_policy = param_dict["use_crisp_policy"]
    is_agent_in_control = param_dict["is_agent_in_control"]

    # --- Run DIBS to convergence ---
    if is_agent_in_control:
        # Run info_sa with the agent controlling the MDP.
        import agent_in_control
        pmf_s_phi, phi_pmf, abstr_policy_pmf = agent_in_control.run_agent_in_control_info_sa(mdp, demo_policy_lambda, beta=beta, is_deterministic_ib=is_deterministic_ib)
    else:
        # Run info_sa.
        from info_sa import run_info_sa
        pmf_s_phi, phi_pmf, abstr_policy_pmf = run_info_sa(mdp, demo_policy_lambda, iters=50, beta=beta, convergence_threshold=0.00001, is_deterministic_ib=is_deterministic_ib)

    print "\tEvaluating..."
    # Make abstract agent.
    from info_sa import get_lambda_policy
    
    # Make the policy deterministic if needed.
    if use_crisp_policy:
        from info_sa import make_policy_det_max_policy
        policy = get_lambda_policy(make_policy_det_max_policy(abstr_policy_pmf))
    else:
        policy = get_lambda_policy(abstr_policy_pmf)

    prob_s_phi = ProbStateAbstraction(phi_pmf)

    # -- Compute Values --

    phi = convert_prob_sa_to_sa(prob_s_phi) if is_deterministic_ib else prob_s_phi
    abstr_agent = AbstractionWrapper(FixedPolicyAgent, state_abstr=phi, agent_params={"policy":policy, "name":"$\\pi_\\phi$"}, name_ext="")
    
    # Compute value of abstract policy w/ coding distribution.
    value = evaluate_agent(agent=abstr_agent, mdp=mdp, instances=100)

    # -- Compute size of S_\phi --
    if is_deterministic_ib:
        s_phi_size = phi.get_num_abstr_states()
    else:
        # TODO: could change this to {s in S : Pr(s) > 0}.
        from rlit_utils import entropy
        s_phi_size = entropy(pmf_s_phi)

    return value, s_phi_size


# -------------------------
# -- Plot States vs. Val --
# -------------------------

def plot_state_size_vs_advantage(directory="info_sa_results_copy", is_deterministic_ib=True, advantage=False, all_points=False):
    '''
    Args:
        directory (str)
        is_deterministic_ib (bool)
        advantage (bool)
        all_points (bool): If true, plots every point, not just the average.

    Summary:
        Takes the current state/
    '''
    method_name = "DIBS" if is_deterministic_ib else "SIBS"
    val_file_name = method_name.lower() + "_val"
    state_file_name = method_name.lower() + "_states"

    # Get average value data.
    value_data, all_value_data = _read_and_average_data_from_policies(file_name=val_file_name, directory=directory)

    # Get average num state data.
    state_data, all_state_data = _read_and_average_data_from_policies(file_name=state_file_name, directory=directory)

    # Convert value to advantage.
    x_axis_name = "$V^{\\pi_\\phi}$"
    if advantage:
        demo_val = float(file(os.path.join(directory, "demo_val.csv")).read().split(",")[0])
        value_data = [demo_val - val for val in value_data]
        for line in all_value_data.keys():
            for i, datum in enumerate(all_value_data[line]):
                all_value_data[line][i] = demo_val - datum
        x_axis_name = "$\\mathbb{E}[V^{\\pi_E} - V^{\\pi_\\phi}]$"

    # Align the state-value pairs and rearrange to align with the RD curve.
    # state_data = [math.ceil(x) for x in state_data]
    state_val_pairs = zip(value_data, state_data)
    sorted_list = sorted(state_val_pairs, key=lambda x: x[0])
    x_axis = [x[0] for x in sorted_list]
    y_axis = [x[1] for x in sorted_list]

    # Plot parameters.
    font = {'size':14}
    matplotlib.rc('font', **font)
    matplotlib.rcParams['pdf.fonttype'] = 42
    # matplotlib.rcParams['text.usetex'] = True
    fig = matplotlib.pyplot.gcf()

    if not advantage:
        # Flip x axis so we mirror the true rate distortion curve.
        ax = pyplot.gca()
        ax.invert_xaxis()

    # Make plot.
    pyplot.plot(x_axis, y_axis,  marker='o', linewidth=3)
    pyplot.xlabel(x_axis_name)
    pyplot.ylabel("$|S_\\phi|$")
    pyplot.title(method_name + ": Rate-Distortion Trade-Off")
    pyplot.grid(True)
    pyplot.tight_layout() # Keeps the spacing nice.

    if all_points:
        x_axis = []
        for key in all_value_data.keys():
            for datum in all_value_data[key]:
                x_axis += [datum]

        y_axis = []
        for key in all_state_data.keys():
            for datum in all_state_data[key]:
                y_axis += [datum]
        
        def sigmoid(x):
            return 1 / (1 + math.e ** -x)
        # colors = [(0.7, min(1.2*sigmoid(x), 1.0), 0.8) for x in x_axis]
        colors = []
        for i, x in enumerate(x_axis):
            y = y_axis[i]
            # colors.append((sigmoid(i**3), 1-  sigmoid(i**3), sigmoid(i**2)))
            colors.append(((sigmoid(y)**3 + 0.7) / 2.0, min(1.2*sigmoid(x), 1.0), 0.8))

        pyplot.scatter(x_axis, y_axis,  marker='.', color=colors)

    # Fill under the curve.
    d = np.zeros(len(y_axis))

    # Save the plot.
    pyplot.savefig(os.path.join(directory, method_name) + "_rate_dist.pdf", format="pdf")
    
    # Open it.
    open_prefix = "gnome-" if sys.platform == "linux" or sys.platform == "linux2" else ""
    os.system(open_prefix + "open " + os.path.join(directory, method_name) + "_rate_dist.pdf")

    # Clear and close.
    pyplot.cla()
    pyplot.close()


def _read_data_from_policies(file_name, directory):
    '''
    Args:
        file_name (list)
        directory (str)

    Returns:
        list
    '''
    # Compute average of each instance.
    next_file_lines = file(os.path.join(directory, str(file_name)) + ".csv").readlines()

    # Grab each line's data, count num lines.
    num_lines = 0
    num_instances = 0
    data_per_line = {} # Key is line number, Val is a list of the data on that line.
    for i, line in enumerate(next_file_lines):
        line = line.strip().split(",")
        if "" in line and len(line) <= 1:
            continue

    return data_per_line

def _read_and_average_data_from_policies(file_name, directory):
    '''
    Args:
        file_name (list)
        directory (str)

    Returns:
        list
        dict
    '''
    # Compute average of each instance.
    next_file_lines = file(os.path.join(directory, str(file_name)) + ".csv").readlines()

    # Grab each line's data, count num lines.
    num_lines = 0
    num_instances = 0
    data_per_line = {} # Key is line number, Val is a list of the data on that line.
    for i, line in enumerate(next_file_lines):
        line = line.strip().split(",")
        if "" in line and len(line) <= 1:
            continue

        data_per_line[i] = [float(val) for val in line if len(val) > 0]
        num_data_per_line = len(data_per_line[i])
        num_lines += 1

    # Compute averages.

    data_indexed_by_beta = [[] * num_lines] * num_data_per_line
    # Should be: beta = 0: [instance_1, instance_2, ...]
    #           beta = 1: [instance_1, instance 2, ...]

    average_data = [0] * num_data_per_line
    for line_number in data_per_line.keys():
        line_data = data_per_line[line_number]


        for index_into_line, val in enumerate(line_data):
            average_data[index_into_line] +=  val / num_lines

            data_indexed_by_beta[index_into_line] += [val]


    return average_data, data_per_line

def main():

    # Params.
    #all_policies = ["$\\pi_E$", "$\\pi_{\\phi,{DIBS}}$", "$\\pi_{\\phi,{SIBS}}$"]

    all_policies = ["dibs_val"]
    # all_policies = ["$\\pi_E$", "AC-$\\pi_{\phi,{DIBS}}$"]#, "ib_val"]
    experiment = "replot_dibs_sibs"

    # Run.
    if experiment == "plot_size_vs_advantage":
        plot_state_size_vs_advantage(advantage=True, all_points=True)
    elif experiment == "replot_dibs_sibs":
        make_beta_val_plot(all_policies, "info_sa_results", is_agent_in_control=False)


if __name__ == "__main__":
    main()
